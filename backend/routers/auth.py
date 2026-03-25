from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas.api import LoginRequest, LoginResponse, UserMeResponse
from ..services.auth_service import AuthError, AuthService
from ..services.snowflake_service import SnowflakeService

logger = logging.getLogger("backend.auth_router")

router = APIRouter(prefix="/auth", tags=["auth"])

_sf_instance: SnowflakeService | None = None
_auth_instance: AuthService | None = None


def get_auth_service() -> AuthService:
    global _sf_instance, _auth_instance
    from ..main import settings
    if _auth_instance is None:
        _sf_instance = SnowflakeService(settings)
        _auth_instance = AuthService(settings, _sf_instance)
    return _auth_instance


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_session),
    auth: AuthService = Depends(get_auth_service),
):
    try:
        result = await auth.login(body.email, body.password, db)
        return LoginResponse(**result)
    except AuthError as e:
        logger.warning("Login failed for %s: %s", body.email, e)
        raise HTTPException(
            status_code=401,
            detail={"status": 401, "title": "Unauthorized", "detail": "Invalid credentials"},
        )
    except Exception as e:
        logger.exception("Login error for %s", body.email)
        raise HTTPException(
            status_code=500,
            detail={"status": 500, "title": "Internal Error", "detail": str(e)},
        )


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_session),
    auth: AuthService = Depends(get_auth_service),
):
    user = request.state.user
    data = await auth.get_me(user, db)
    return UserMeResponse(**data)
