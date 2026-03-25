from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import AuthContext, get_current_user
from backend.v2.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)
from backend.v2.modules.auth.service import AuthService
from backend.v2.shared.response import success_response
from backend.v2.config.settings import Settings

router = APIRouter(tags=["auth-v1-compat"])


def _get_auth_service(db: AsyncSession) -> AuthService:
    from backend.v2.main import settings
    return AuthService(settings, db)


@router.post("/auth/login")
async def login_v1(body: LoginRequest, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    result = await service.login(body.email, body.password)
    return JSONResponse(status_code=200, content={
        "access_token": result["access_token"],
        "token_type": "Bearer",
        "expires_in": result["expires_in"],
        "role": result["user"]["role"],
        "roles": result.get("roles", [result["user"]["role"]]),
        "user_id": result["user"]["user_id"],
        "display_name": result["user"]["name"],
    })


@router.post("/auth/refresh")
async def refresh_v1(body: dict, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    refresh_token = body.get("refresh_token", "")
    result = await service.refresh(refresh_token)
    return JSONResponse(status_code=200, content={
        "access_token": result["access_token"],
        "token_type": "Bearer",
        "expires_in": result["expires_in"],
    })


@router.post("/auth/logout")
async def logout_v1(body: dict, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    refresh_token = body.get("refresh_token", "")
    await service.logout(refresh_token)
    return JSONResponse(status_code=200, content={"logged_out": True})


@router.post("/auth/forgot-password")
async def forgot_password_v1(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    await service.forgot_password(body.email)
    return JSONResponse(status_code=200, content={"message": "If the email exists, a reset link has been sent"})


@router.post("/auth/reset-password")
async def reset_password_v1(body: ResetPasswordRequest, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    await service.reset_password(body.token, body.password)
    return JSONResponse(status_code=200, content={"message": "Password reset successfully"})


@router.get("/auth/me")
async def get_me_v1(ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    result = await service.get_me(ctx.user_id)
    return JSONResponse(status_code=200, content={
        "user_id": result["user_id"],
        "email": result["email"],
        "display_name": result["name"],
        "role": result["role"],
        "roles": result.get("roles", [result["role"]]),
        "status": result.get("status", "active"),
    })


@router.post("/api/auth/login")
async def login_v2(body: LoginRequest, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    result = await service.login(body.email, body.password)
    return success_response(result)


@router.post("/api/auth/refresh")
async def refresh_v2(body: dict, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    refresh_token = body.get("refresh_token", "")
    result = await service.refresh(refresh_token)
    return success_response(result)


@router.post("/api/auth/logout")
async def logout_v2(body: dict, db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    refresh_token = body.get("refresh_token", "")
    await service.logout(refresh_token)
    return success_response({"logged_out": True})


@router.get("/api/auth/me")
async def get_me_v2(ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_auth_service(db)
    result = await service.get_me(ctx.user_id)
    return success_response(result)
