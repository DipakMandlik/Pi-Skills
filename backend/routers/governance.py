"""
Governance Router - Central AI request endpoint with full governance
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings
from ..core.database import get_session
from ..schemas.api import (
    GovernanceRequest,
    GovernanceResponse,
    GovernanceValidateRequest,
    GovernanceValidateResponse,
)
from ..services.governance_service import GovernanceService

logger = logging.getLogger("backend.governance_router")

router = APIRouter(prefix="/ai", tags=["governance"])


def _get_settings() -> Settings:
    from ..main import settings
    return settings


@router.post("/request", response_model=GovernanceResponse)
async def ai_request(
    body: GovernanceRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    settings = _get_settings()
    governance = GovernanceService(settings, db)

    result = await governance.process_request(
        user=user,
        prompt=body.prompt,
        model_id=body.model_id,
        task_type=body.task_type,
        skill_id=body.skill_id,
        max_tokens=body.max_tokens,
        parameters=body.parameters,
    )

    if result["status"] == "denied":
        raise HTTPException(
            status_code=403,
            detail={
                "status": 403,
                "title": "Access Denied",
                "detail": result.get("reason", "UNKNOWN"),
                "message": result.get("message", ""),
                "request_id": result["request_id"],
            },
        )

    if result["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail={
                "status": 500,
                "title": "Internal Error",
                "detail": result.get("error", "Unknown error"),
                "request_id": result["request_id"],
            },
        )

    return GovernanceResponse(**result)


@router.post("/validate", response_model=GovernanceValidateResponse)
async def validate_request(
    body: GovernanceValidateRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    settings = _get_settings()
    governance = GovernanceService(settings, db)

    result = await governance.validate_request(
        user=user,
        model_id=body.model_id,
        task_type=body.task_type,
        estimated_tokens=body.estimated_tokens,
    )

    return GovernanceValidateResponse(**result)


@router.get("/dashboard")
async def user_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    settings = _get_settings()
    governance = GovernanceService(settings, db)

    return await governance.get_user_dashboard(user.user_id)


@router.get("/tokens")
async def get_token_usage(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    from ..services.token_service import TokenService

    token_svc = TokenService(db)
    usage = await token_svc.get_user_token_usage(user.user_id)
    stats = await token_svc.get_token_usage_stats(user.user_id)

    return {
        "usage": usage,
        "stats": stats,
    }
