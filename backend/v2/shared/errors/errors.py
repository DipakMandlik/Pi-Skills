from __future__ import annotations


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: list[str] | None = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


class ValidationError(AppError):
    status_code: int = 400
    code: str = "VALIDATION_ERROR"


class AuthenticationError(AppError):
    status_code: int = 401
    code: str = "AUTHENTICATION_ERROR"


class AuthorizationError(AppError):
    status_code: int = 403
    code: str = "AUTHORIZATION_ERROR"


class NotFoundError(AppError):
    status_code: int = 404
    code: str = "NOT_FOUND"


class ConflictError(AppError):
    status_code: int = 409
    code: str = "CONFLICT"


class RateLimitError(AppError):
    status_code: int = 429
    code: str = "RATE_LIMIT_EXCEEDED"


class InternalError(AppError):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
