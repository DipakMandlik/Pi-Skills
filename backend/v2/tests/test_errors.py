from __future__ import annotations

import pytest

from backend.v2.shared.errors import (
    AppError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    InternalError,
)


def test_app_error_defaults():
    err = AppError("Something went wrong")
    assert err.status_code == 500
    assert err.code == "INTERNAL_ERROR"
    assert err.message == "Something went wrong"
    assert err.details == []


def test_app_error_with_details():
    err = AppError("Bad", details=["field1 is required"])
    assert err.details == ["field1 is required"]


def test_validation_error():
    err = ValidationError("Invalid input", details=["email is required"])
    assert err.status_code == 400
    assert err.code == "VALIDATION_ERROR"


def test_authentication_error():
    err = AuthenticationError("Token expired")
    assert err.status_code == 401
    assert err.code == "AUTHENTICATION_ERROR"


def test_authorization_error():
    err = AuthorizationError("Admin required")
    assert err.status_code == 403
    assert err.code == "AUTHORIZATION_ERROR"


def test_not_found_error():
    err = NotFoundError("Resource not found")
    assert err.status_code == 404
    assert err.code == "NOT_FOUND"


def test_conflict_error():
    err = ConflictError("Already exists")
    assert err.status_code == 409
    assert err.code == "CONFLICT"


def test_rate_limit_error():
    err = RateLimitError("Too many requests")
    assert err.status_code == 429
    assert err.code == "RATE_LIMIT_EXCEEDED"


def test_internal_error():
    err = InternalError("DB connection lost")
    assert err.status_code == 500
    assert err.code == "INTERNAL_ERROR"
