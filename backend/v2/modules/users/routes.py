from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import AuthContext, get_current_user
from backend.v2.modules.users.schemas import (
    InviteByEmailRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from backend.v2.modules.users.service import UserService
from backend.v2.shared.response import created_response, no_content_response, success_response

router = APIRouter(prefix="/api/users", tags=["users"])


def _get_user_service(db: AsyncSession) -> UserService:
    return UserService(db)


@router.get("")
async def list_users(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    role: str = Query(""),
    status: str = Query(""),
):
    service = _get_user_service(db)
    items, total = await service.list_users(ctx.org_id, page, page_size, search, role, status)
    return success_response(
        items,
        {"page": page, "total": total, "per_page": page_size, "total_pages": math.ceil(total / page_size) if total > 0 else 0},
    )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    result = await service.get_user(ctx.org_id, user_id)
    return success_response(result)


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    kwargs = body.model_dump(exclude_none=True)
    result = await service.update_user(ctx.org_id, user_id, **kwargs)
    return success_response(result)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    await service.delete_user(ctx.org_id, user_id)
    return no_content_response()


@router.get("/{user_id}/skills")
async def get_user_skills(
    user_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    skills = await service.get_user_skills(ctx.org_id, user_id)
    return success_response(skills)


@router.post("/{user_id}/skills/assign")
async def assign_skills(
    user_id: str,
    body: dict,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    skill_ids = body.get("skill_ids", [])
    result = await service.assign_skills(ctx.org_id, user_id, skill_ids, ctx.user_id)
    return created_response(result)


@router.delete("/{user_id}/skills/{skill_id}")
async def remove_skill(
    user_id: str,
    skill_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    await service.remove_skill(ctx.org_id, user_id, skill_id)
    return no_content_response()


@router.post("/invite")
async def invite_by_email(
    body: InviteByEmailRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    result = await service.invite_by_email(ctx.org_id, body.email, body.role, ctx.user_id)
    return created_response(result)
