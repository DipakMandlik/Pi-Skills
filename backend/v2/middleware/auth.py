from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.config.settings import Settings
from backend.v2.database.client import RefreshTokenModel, get_session
from backend.v2.shared.errors import AuthenticationError, AuthorizationError
from backend.v2.shared.logger import get_logger, set_request_context

logger = get_logger("middleware.auth")

PUBLIC_PATHS = {
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/auth/login",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/health",
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc",
}


class AuthContext:
    def __init__(self, user_id: str, org_id: str, email: str, name: str, role: str, roles: list[str]):
        self.user_id = user_id
        self.org_id = org_id
        self.email = email
        self.name = name
        self.role = role
        self.roles = roles

    def has_role(self, required: str) -> bool:
        hierarchy = {"OWNER": ["OWNER", "ADMIN", "MEMBER", "VIEWER"], "ADMIN": ["ADMIN", "MEMBER", "VIEWER"], "MEMBER": ["MEMBER", "VIEWER"], "VIEWER": ["VIEWER"]}
        user_roles = set()
        for r in self.roles:
            user_roles.update(hierarchy.get(r.upper(), [r.upper()]))
        return required.upper() in user_roles


def _decode_token(token: str, secret: str, algorithm: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> AuthContext:
    if request.url.path in PUBLIC_PATHS:
        return AuthContext(user_id="", org_id="", email="", name="", role="", roles=[])

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = auth_header[7:]
    settings: Settings = request.app.state.settings
    payload = _decode_token(token, settings.jwt_secret, settings.jwt_algorithm)

    user_id = payload.get("sub")
    org_id = payload.get("org_id")
    email = payload.get("email", "")
    name = payload.get("name", "")
    role = payload.get("role", "VIEWER")
    roles = payload.get("roles", [role])

    if not user_id or not org_id:
        raise AuthenticationError("Invalid token payload")

    ctx = AuthContext(user_id=user_id, org_id=org_id, email=email, name=name, role=role, roles=roles)
    set_request_context(getattr(request.state, "request_id", ""), user_id)
    return ctx


async def require_admin(ctx: AuthContext = Depends(get_current_user)) -> AuthContext:
    if not ctx.has_role("ADMIN"):
        raise AuthorizationError("Admin role required")
    return ctx


async def require_owner(ctx: AuthContext = Depends(get_current_user)) -> AuthContext:
    if not ctx.has_role("OWNER"):
        raise AuthorizationError("Owner role required")
    return ctx
