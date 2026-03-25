"""Shared constants for AI Governance Platform."""

from enum import IntEnum

class HTTPStatus(IntEnum):
    """HTTP status codes."""
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    RATE_LIMITED = 429
    INTERNAL_SERVER_ERROR = 500

class AppConstants:
    """Application constants."""
    JWT_EXPIRE_HOURS = 24
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_PROMPT_LENGTH = 50000
    REDIS_PERM_TTL = 60
    REDIS_MODEL_TTL = 300
    REDIS_RATE_WINDOW = 60

class ErrorMessages:
    """Error message constants."""
    INVALID_CREDENTIALS = "Invalid email or password"
    TOKEN_EXPIRED = "Authentication token has expired"
    TOKEN_INVALID = "Authentication token is invalid"
    INSUFFICIENT_PERMISSIONS = "You do not have permission to perform this action"
    SKILL_NOT_FOUND = "The requested skill does not exist"
    MODEL_NOT_FOUND = "The requested model does not exist"
    SKILL_NOT_ASSIGNED = "You do not have access to this skill"
    MODEL_NOT_PERMITTED = "You do not have permission to use this model"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later"
    PROMPT_VIOLATION = "Your prompt violates security policies"

__all__ = ["HTTPStatus", "AppConstants", "ErrorMessages"]
