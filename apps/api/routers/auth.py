from __future__ import annotations

import json
import logging
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..schemas.api import LoginRequest, LoginResponse, UserMeResponse

logger = logging.getLogger("backend.auth_router")

router = APIRouter(prefix="/auth", tags=["auth"])

DEV_ENVS = {"dev", "development", "local", "test"}


def _deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Tue, 30 Jun 2026 00:00:00 GMT"
    response.headers["Warning"] = '299 apps-api "Deprecated auth path. Use backend /auth endpoints."'
    response.headers["Link"] = '</auth>; rel="successor-version"'


def _proxy_request(
    *,
    method: str,
    path: str,
    payload: dict | None = None,
    auth_header: str | None = None,
) -> dict:
    from ..main import settings

    if settings.app_env not in DEV_ENVS:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "status": 410,
                "title": "Deprecated",
                "detail": "apps/api auth routes are disabled outside dev/test. Use backend /auth endpoints.",
            },
        )

    if not settings.apps_api_auth_proxy_enabled:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "status": 410,
                "title": "Deprecated",
                "detail": "apps/api auth routes are deprecated and disabled. Use backend /auth endpoints.",
            },
        )

    base_url = settings.governance_backend_url.rstrip("/")
    url = f"{base_url}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header

    req = urllib_request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=settings.governance_auth_timeout_seconds) as upstream:
            raw = upstream.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            if not isinstance(parsed, dict):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "status": 502,
                        "title": "Upstream Error",
                        "detail": "Unexpected non-object auth response from backend service.",
                    },
                )
            return parsed
    except urllib_error.HTTPError as exc:
        detail_payload: dict | str = ""
        try:
            raw = exc.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            detail_payload = parsed if isinstance(parsed, dict) else str(parsed)
        except Exception:
            detail_payload = exc.reason or "Auth proxy request failed"
        raise HTTPException(status_code=exc.code, detail=detail_payload)
    except urllib_error.URLError as exc:
        logger.warning("Auth proxy unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": 503,
                "title": "Service Unavailable",
                "detail": "Canonical backend auth service is unavailable.",
            },
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
):
    _deprecation_headers(response)
    result = _proxy_request(method="POST", path="/auth/login", payload=body.model_dump())
    return LoginResponse(**result)


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    request: Request,
    response: Response,
):
    _deprecation_headers(response)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": 401, "title": "Unauthorized", "detail": "Missing or invalid authorization header"},
        )
    data = _proxy_request(method="GET", path="/auth/me", auth_header=auth_header)
    return UserMeResponse(**data)
