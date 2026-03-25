from __future__ import annotations

import logging
from typing import Optional

import jwt
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from ..core.config import Settings
from ..models.domain import AuthUser

logger = logging.getLogger("backend.auth_middleware")

PUBLIC_PATHS = {"/auth/login", "/health", "/docs", "/openapi.json", "/redoc"}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _error_response(401, "Unauthorized", "Missing or invalid authorization header")

        token = auth_header[7:]
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

        request_id = getattr(request.state, "request_id", "")
        request.state.user = AuthUser(
            user_id=payload["sub"],
            email=payload.get("email", ""),
            role=payload.get("role", "viewer"),
            display_name=payload.get("display_name", ""),
            request_id=request_id,
            token_exp=payload.get("exp", 0),
        )

        return await call_next(request)


def _error_response(status: int, title: str, detail: str) -> Response:
    import json
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=status,
        content={"status": status, "title": title, "detail": detail},
    )
