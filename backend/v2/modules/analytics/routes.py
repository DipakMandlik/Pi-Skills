from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import AuthContext, get_current_user
from backend.v2.modules.analytics.service import AnalyticsService
from backend.v2.shared.response import success_response

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _get_analytics_service(db: AsyncSession) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/skill-usage")
async def get_skill_usage(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    limit: int = Query(10, ge=1, le=100),
):
    service = _get_analytics_service(db)
    result = await service.get_skill_usage(ctx.org_id, limit)
    return success_response(result)


@router.get("/skill-errors")
async def get_skill_errors(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
):
    service = _get_analytics_service(db)
    result = await service.get_skill_errors(ctx.org_id, limit)
    return success_response(result)


@router.get("/user-activity")
async def get_user_activity(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
):
    service = _get_analytics_service(db)
    result = await service.get_user_activity(ctx.org_id, limit)
    return success_response(result)


@router.get("/trends")
async def get_trends(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    days: int = Query(30, ge=1, le=365),
):
    service = _get_analytics_service(db)
    result = await service.get_trends(ctx.org_id, days)
    return success_response(result)
