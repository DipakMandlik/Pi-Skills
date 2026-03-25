"""Custom exceptions for AI Governance Platform."""

from typing import Any

class BaseAPIException(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: dict[str, Any] | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class AuthenticationError(BaseAPIException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None):
        super().__init__(message, 401, details)

class AuthorizationError(BaseAPIException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Permission denied", details: dict[str, Any] | None = None):
        super().__init__(message, 403, details)

class NotFoundError(BaseAPIException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(message, 404, details)

class ConflictError(BaseAPIException):
    """Raised when there's a conflict with existing resource."""
    
    def __init__(self, message: str = "Resource conflict", details: dict[str, Any] | None = None):
        super().__init__(message, 409, details)

class ValidationError(BaseAPIException):
    """Raised when validation fails."""
    
    def __init__(self, message: str = "Validation failed", details: dict[str, Any] | None = None):
        super().__init__(message, 422, details)

class RateLimitError(BaseAPIException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: dict[str, Any] | None = None):
        super().__init__(message, 429, details)

class ModelNotFoundError(NotFoundError):
    """Raised when a model is not found."""
    pass

class SkillNotFoundError(NotFoundError):
    """Raised when a skill is not found."""
    pass

class PermissionDeniedError(AuthorizationError):
    """Raised when permission is denied."""
    pass

__all__ = [
    "BaseAPIException",
    "AuthenticationError",
    "AuthorizationError", 
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "ModelNotFoundError",
    "SkillNotFoundError",
    "PermissionDeniedError",
]
