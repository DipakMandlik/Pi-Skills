from __future__ import annotations

from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.v2.shared.errors import AppError, AuthenticationError, ValidationError, NotFoundError
from backend.v2.shared.logger import get_logger

logger = get_logger("middleware.error_handler")

V1_PATHS = {"/skills", "/users", "/auth/login", "/auth/refresh", "/auth/logout", "/auth/me", "/auth/forgot-password", "/auth/reset-password"}


def _is_v1_path(path: str) -> bool:
    if path in V1_PATHS:
        return True
    if path.startswith("/skills/") or path.startswith("/users/"):
        return True
    return False


async def error_handler_middleware(request: Request, call_next: Callable) -> JSONResponse:
    try:
        return await call_next(request)
    except AppError as e:
        logger.warning("AppError: %s - %s", e.code, e.message)
        if _is_v1_path(request.url.path):
            detail = e.message
            if e.details:
                detail = "; ".join(e.details)
            body = {"detail": detail, "message": e.message, "status": e.status_code, "title": e.code}
            return JSONResponse(status_code=e.status_code, content=body)
        body = {"success": False, "error": {"code": e.code, "message": e.message}}
        if e.details:
            body["error"]["details"] = e.details
        return JSONResponse(status_code=e.status_code, content=body)
    except Exception as e:
        logger.exception("Unhandled exception: %s", str(e))
        if _is_v1_path(request.url.path):
            body = {"detail": "An unexpected error occurred", "message": "Internal server error", "status": 500, "title": "INTERNAL_ERROR"}
            return JSONResponse(status_code=500, content=body)
        body = {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}
        return JSONResponse(status_code=500, content=body)
