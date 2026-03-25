"""Utility functions for AI Governance Platform."""

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

T = TypeVar("T")

def generate_random_string(length: int = 32) -> str:
    """Generate a cryptographically secure random string."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)

def generate_uuid() -> str:
    """Generate a UUID4 string."""
    import uuid
    return str(uuid.uuid4())

class Result(Generic[T]):
    """Result wrapper for operations that can fail."""
    
    def __init__(self, value: T | None = None, error: str | None = None):
        self._value = value
        self._error = error
    
    @property
    def is_ok(self) -> bool:
        return self._error is None
    
    @property
    def is_err(self) -> bool:
        return not self.is_ok
    
    @property
    def value(self) -> T:
        if self._error:
            raise ValueError(f"Cannot get value from error: {self._error}")
        return self._value
    
    @property
    def error(self) -> str | None:
        return self._error
    
    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        return cls(value=value)
    
    @classmethod
    def err(cls, error: str) -> "Result[T]":
        return cls(error=error)

def safe_dict_get(d: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary value."""
    result = d
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result if result is not None else default

__all__ = [
    "generate_random_string",
    "utc_now", 
    "generate_uuid",
    "Result",
    "safe_dict_get",
]
