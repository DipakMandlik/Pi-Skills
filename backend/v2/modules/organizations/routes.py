from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import AuthContext, get_current_user
from backend.v2.modules.organizations.schemas import OrgUpdateRequest
from backend.v2.modules.organizations.service import OrgService
from backend.v2.shared.response import success_response

router = APIRouter(prefix="/api/org", tags=["organizations"])


def _get_org_service(db: AsyncSession) -> OrgService:
    return OrgService(db)


@router.get("")
async def get_my_org(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_org_service(db)
    result = await service.get_org(ctx.org_id)
    return success_response(result)


@router.patch("")
async def update_org(
    body: OrgUpdateRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_org_service(db)
    kwargs = body.model_dump(exclude_none=True)
    result = await service.update_org(ctx.org_id, **kwargs)
    return success_response(result)


@router.get("/stats")
async def get_org_stats(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_org_service(db)
    result = await service.get_stats(ctx.org_id)
    return success_response(result)


@router.get("/activity")
async def get_org_activity(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = _get_org_service(db)
    items, total = await service.get_activity(ctx.org_id, page, page_size)
    return success_response(items, {"page": page, "total": total, "per_page": page_size, "total_pages": (total + page_size - 1) // page_size})
