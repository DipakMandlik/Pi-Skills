from __future__ import annotations

import json
import logging
import threading
import hashlib
import secrets
from contextlib import asynccontextmanager
from typing import Any
from datetime import datetime, timedelta, timezone

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import load_settings, validate_jwt_secret, validate_required_env
from .session_store import SessionStore
from .security import ValidationError, sanitize_error
from .snowflake_client import SnowflakeClient, SnowflakeClientUnavailableError
from .tool_registry import ToolRegistry

settings = load_settings()
logging.basicConfig(level=getattr(logging, settings.mcp_log_level.upper(), logging.INFO))
logger = logging.getLogger("snowflake-mcp")


def _configure_third_party_logging() -> None:
    level = getattr(logging, settings.snowflake_log_level.upper(), logging.ERROR)
    logging.getLogger("snowflake").setLevel(level)
    logging.getLogger("snowflake.connector").setLevel(level)
    logging.getLogger("snowflake.connector.connection").setLevel(level)
    logging.getLogger("snowflake.connector.vendored.urllib3").setLevel(level)
    logging.getLogger("snowflake.connector.vendored.urllib3.connectionpool").setLevel(level)
    logging.getLogger("urllib3.connectionpool").setLevel(level)
    logging.getLogger("botocore").setLevel(level)


_configure_third_party_logging()

app = FastAPI(title="Snowflake MCP Bridge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.mcp_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
registry = ToolRegistry(settings=settings, sf=SnowflakeClient(settings))
session_store = SessionStore(settings.mcp_session_database_url, settings.jwt_secret)


# ── Auth Session Store (persistent) ──

_rate_limits: dict[str, tuple[float, int]] = {}
_rate_limit_lock = threading.Lock()


def _store_token(user_info: dict[str, Any]) -> tuple[str, str]:
    return session_store.issue_session(user_info)


def _validate_token(token: str) -> dict[str, Any] | None:
    return session_store.validate_access_token(token)


def _refresh_session(refresh_token: str) -> tuple[str, str] | None:
    return session_store.refresh_session(refresh_token)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    value = authorization.strip()
    prefix = "Bearer "
    if not value.lower().startswith(prefix.lower()):
        return ""
    return value[len(prefix):].strip()


def _require_authenticated_user(authorization: str | None) -> tuple[str, dict[str, Any]]:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    user = _validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token, user


def _enforce_rate_limit(token: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    window_seconds = 60.0
    with _rate_limit_lock:
        window_start, count = _rate_limits.get(token, (now, 0))
        if now - window_start >= window_seconds:
            window_start = now
            count = 0

        count += 1
        _rate_limits[token] = (window_start, count)

        if count > settings.mcp_rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: max {settings.mcp_rate_limit_per_minute} requests/min",
            )


def _validate_argument_payload(arguments: dict[str, Any]) -> None:
    payload = json.dumps(arguments, separators=(",", ":"), ensure_ascii=True)
    payload_size = len(payload.encode("utf-8"))
    if payload_size > settings.mcp_max_arguments_bytes:
        raise ValidationError(
            f"arguments payload exceeds limit ({payload_size} bytes > {settings.mcp_max_arguments_bytes} bytes)"
        )

    def _walk(value: Any, path: str = "arguments") -> None:
        if isinstance(value, str):
            if len(value) > settings.mcp_max_argument_length:
                raise ValidationError(
                    f"{path} exceeds max length ({len(value)} > {settings.mcp_max_argument_length})"
                )
            return
        if isinstance(value, dict):
            for key, item in value.items():
                _walk(item, f"{path}.{key}")
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                _walk(item, f"{path}[{index}]")

    _walk(arguments)


def _run_startup_checks() -> None:
    try:
        validate_jwt_secret(settings.jwt_secret)
        logger.info("startup_preflight_passed check=jwt_secret")
    except ValueError as exc:
        logger.error("startup_preflight_failed check=jwt_secret detail=%s", sanitize_error(exc))
        raise


def _start_session_cleanup_loop() -> None:
    def _cleanup_worker() -> None:
        while True:
            try:
                session_store.cleanup_expired()
            except Exception as exc:
                logger.warning("session_cleanup_failed: %s", sanitize_error(exc))
            threading.Event().wait(600)

    threading.Thread(target=_cleanup_worker, daemon=True).start()


def _start_snowflake_warmup() -> None:
    def _warmup() -> None:
        try:
            registry.sf.execute_query("SELECT 1")
            logger.info("snowflake_warmup_success")
        except Exception as exc:
            logger.warning("snowflake_warmup_failed: %s", sanitize_error(exc))

    threading.Thread(target=_warmup, daemon=True).start()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _run_startup_checks()
    _start_session_cleanup_loop()
    _start_snowflake_warmup()
    yield


app.router.lifespan_context = lifespan


# ── Request Models ──

class ToolCallRequest(BaseModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthRefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=1)


class AuthLogoutRequest(BaseModel):
    refreshToken: str | None = None


# ── Routes ──

@app.get("/health")
def health() -> dict[str, Any]:
    missing = validate_required_env(settings)
    connector_ready = True
    connector_message = None
    try:
        registry.sf._load_connector()
    except SnowflakeClientUnavailableError as exc:
        connector_ready = False
        connector_message = str(exc)

    return {
        "status": "ok" if (not missing and connector_ready) else "degraded",
        "missing_env": missing,
        "sql_safety_mode": settings.sql_safety_mode,
        "snowflake_connector_ready": connector_ready,
        "snowflake_connector_message": connector_message,
    }


@app.post("/auth/login")
def auth_login(request: AuthLoginRequest) -> dict[str, Any]:
    """Authenticate user against Snowflake credentials."""
    try:
        connector = registry.sf._load_connector()
        conn = connector.connect(
            account=settings.snowflake_account,
            user=request.email,
            password=request.password,
            role=settings.snowflake_role,
            warehouse=settings.snowflake_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            login_timeout=10,
        )
        conn.close()

        # Determine role based on Snowflake role
        is_admin = settings.snowflake_role.upper() in ("ACCOUNTADMIN", "SYSADMIN", "SECURITYADMIN")

        user_info = {
            "id": hashlib.md5(request.email.encode()).hexdigest()[:12],
            "email": request.email,
            "name": request.email.split("@")[0].replace(".", " ").title(),
            "role": "ADMIN" if is_admin else "USER",
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        token, refresh_token = _store_token(user_info)
        logger.info("auth_login_success user=%s", request.email)

        return {
            "token": token,
            "refreshToken": refresh_token,
            "user": user_info,
        }
    except Exception as exc:
        logger.warning("auth_login_failed user=%s error=%s", request.email, sanitize_error(exc))
        raise HTTPException(status_code=401, detail="Invalid Snowflake credentials")


@app.post("/auth/refresh")
def auth_refresh(request: AuthRefreshRequest) -> dict[str, Any]:
    refreshed = _refresh_session(request.refreshToken)
    if not refreshed:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    token, refresh_token = refreshed
    user = _validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Failed to refresh session")
    return {
        "token": token,
        "refreshToken": refresh_token,
        "user": user,
    }


@app.post("/auth/logout")
def auth_logout(
    request: AuthLogoutRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    revoked = session_store.revoke_by_access_token(token)
    if not revoked and request.refreshToken:
        revoked = session_store.revoke_by_refresh_token(request.refreshToken)
    if not revoked:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"revoked": True}


@app.get("/users/me")
def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Get current user from token."""
    _, user = _require_authenticated_user(authorization)
    return user


@app.get("/mcp/tools")
def list_tools(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if settings.mcp_auth_required:
        token, _ = _require_authenticated_user(authorization)
        _enforce_rate_limit(token)

    tools = []
    for tool in registry.list_tools():
        tools.append(
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "outputSchema": tool.output_schema,
            }
        )
    return {"tools": tools}


@app.post("/mcp/call")
def call_tool(request: ToolCallRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    try:
        if settings.mcp_auth_required:
            token, _ = _require_authenticated_user(authorization)
            _enforce_rate_limit(token)

        _validate_argument_payload(request.arguments)
        result = registry.run_tool(request.name, request.arguments)
        logger.info("tool_call_success name=%s", request.name)
        return {"ok": True, "name": request.name, "result": result}
    except ValidationError as exc:
        logger.warning("tool_call_validation_error name=%s error=%s", request.name, exc)
        raise HTTPException(status_code=400, detail=sanitize_error(exc)) from exc
    except Exception as exc:
        logger.exception("tool_call_failed name=%s", request.name)
        raise HTTPException(status_code=500, detail=sanitize_error(exc)) from exc


@app.get("/mcp/events")
def mcp_events(authorization: str | None = Header(default=None)) -> StreamingResponse:
    if settings.mcp_auth_required:
        token, _ = _require_authenticated_user(authorization)
        _enforce_rate_limit(token)

    def event_stream():
        payload = {
            "event": "server_ready",
            "tools": [t.name for t in registry.list_tools()],
            "sql_safety_mode": settings.sql_safety_mode,
        }
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def run() -> None:
    uvicorn.run(
        "apps.mcp.main:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=False,
        log_level=settings.mcp_log_level.lower(),
    )


if __name__ == "__main__":
    run()
