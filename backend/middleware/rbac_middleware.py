"""
RBAC Middleware — Enhanced JWT auth with 8-role support, API-level access control.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps

import jwt
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from ..core.config import Settings
from ..core.rbac import (
    can_access_api_endpoint,
    validate_agent_access,
)
from ..models.domain import AuthUser

logger = logging.getLogger("backend.rbac_middleware")

PUBLIC_PATHS = {
    "/auth/login",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Paths that bypass RBAC enforcement but still require auth
AUTH_ONLY_PATHS = {
    "/auth/me",
}

LEGACY_ROLE_MAP = {
    "ADMIN": "ORG_ADMIN",
    "USER": "BUSINESS_USER",
}


def _normalize_role(role: str) -> str:
    normalized = (role or "VIEWER").upper().strip()
    return LEGACY_ROLE_MAP.get(normalized, normalized)


class RBACAuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication + RBAC authorization middleware."""

    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        method = request.method

        # Skip auth for public paths and OPTIONS
        if path in PUBLIC_PATHS or method == "OPTIONS":
            return await call_next(request)

        # Extract and validate JWT
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _error_response(401, "Unauthorized", "Missing or invalid authorization header")

        token = auth_header[7:]
        payload = None
        request_id = getattr(request.state, "request_id", "")
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            return _error_response(401, "Unauthorized", "Token expired")
        except jwt.InvalidTokenError:
            return _error_response(401, "Unauthorized", "Invalid token")

        # Build AuthUser with multi-role support
        roles = payload.get("roles", [])
        primary_role = payload.get("role", "VIEWER")
        if not roles:
            roles = [primary_role]

        roles = [_normalize_role(r) for r in roles]
        primary_role = _normalize_role(primary_role)

        request.state.user = AuthUser(
            user_id=payload["sub"],
            email=payload.get("email", ""),
            role=primary_role,
            roles=roles,
            display_name=payload.get("display_name", ""),
            request_id=request_id,
            token_exp=payload.get("exp", 0),
        )

        # Skip RBAC check for auth-only paths
        if path in AUTH_ONLY_PATHS:
            return await call_next(request)

        # RBAC enforcement
        if not _check_access(roles, path, method):
            logger.warning(
                "RBAC denied: user=%s roles=%s path=%s method=%s",
                payload.get("email", "unknown"), roles, path, method,
            )
            return _error_response(
                403, "Forbidden",
                f"Role(s) {roles} not authorized for {method} {path}",
            )

        return await call_next(request)

def _check_access(roles: list[str], path: str, method: str) -> bool:
    """Check if any of the user's roles grant access to the endpoint."""
    for role in roles:
        if can_access_api_endpoint(role, path, method):
            return True
    return False


def _error_response(status: int, title: str, detail: str) -> Response:
    return JSONResponse(
        status_code=status,
        content={"status": status, "title": title, "detail": detail},
    )


# ── Decorator for route-level role enforcement ─────────────

def require_roles(*allowed_roles: str):
    """Decorator to restrict endpoint access to specific roles."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user: AuthUser = request.state.user
            user_roles = {r.upper() for r in user.roles}
            allowed = {r.upper() for r in allowed_roles}

            if not user_roles.intersection(allowed):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "status": 403,
                        "title": "Forbidden",
                        "detail": f"Required role(s): {', '.join(allowed_roles)}. Your roles: {', '.join(user.roles)}",
                    },
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_admin(request: Request) -> AuthUser:
    """Helper to enforce admin-level access (ORG_ADMIN or SECURITY_ADMIN)."""
    user: AuthUser = request.state.user
    admin_roles = {"ORG_ADMIN", "SECURITY_ADMIN"}
    user_roles = {r.upper() for r in user.roles}

    if not user_roles.intersection(admin_roles):
        raise HTTPException(
            status_code=403,
            detail={
                "status": 403,
                "title": "Forbidden",
                "detail": "Admin role required (ORG_ADMIN or SECURITY_ADMIN)",
            },
        )
    return user


def require_role_inheritance(request: Request, required_role: str) -> AuthUser:
    """Check if user's role hierarchy includes the required role."""
    from ..core.rbac import get_inherited_roles

    user: AuthUser = request.state.user
    for user_role in user.roles:
        inherited = get_inherited_roles(user_role)
        if required_role.upper() in inherited:
            return user

    raise HTTPException(
        status_code=403,
        detail={
            "status": 403,
            "title": "Forbidden",
            "detail": f"Role {required_role} or higher required",
        },
    )


def require_agent_scope(agent_id: str, target_schema: str, action: str):
    """Validate AI agent access scope."""
    if not validate_agent_access(agent_id, target_schema, action):
        raise HTTPException(
            status_code=403,
            detail={
                "status": 403,
                "title": "Agent Access Denied",
                "detail": f"Agent '{agent_id}' cannot perform '{action}' on '{target_schema}'",
            },
        )
