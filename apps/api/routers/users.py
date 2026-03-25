from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import (
    ModelPermissionModel,
    SkillAssignmentModel,
    UserModel,
    get_session,
)
from ..schemas.api import UserListItem, UserListResponse

logger = logging.getLogger("backend.users_router")

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    request: Request,
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    current_user = request.state.user
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": 403, "title": "Access Denied", "detail": "Admin role required"},
        )

    filters = []
    if role:
        filters.append(UserModel.platform_role == role)
    if is_active is not None:
        filters.append(UserModel.is_active == is_active)

    where_clause = filters[0] if len(filters) == 1 else (filters[0] if not filters else filters[0])
    for f in filters[1:]:
        where_clause = where_clause & f

    count_q = select(func.count()).select_from(UserModel)
    if filters:
        count_q = count_q.where(where_clause)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = select(UserModel).order_by(UserModel.created_at.desc()).offset(offset).limit(page_size)
    if filters:
        query = query.where(where_clause)
    result = await db.execute(query)
    users_orm = result.scalars().all()

    users = []
    for u in users_orm:
        model_perms = await db.execute(
            select(ModelPermissionModel.model_id).where(
                ModelPermissionModel.user_id == u.id,
                ModelPermissionModel.is_active == True,
            )
        )
        allowed_models = [r[0] for r in model_perms.all()]

        skill_perms = await db.execute(
            select(SkillAssignmentModel.skill_id).where(
                SkillAssignmentModel.user_id == u.id,
                SkillAssignmentModel.is_active == True,
            )
        )
        allowed_skills = [r[0] for r in skill_perms.all()]

        users.append(UserListItem(
            user_id=str(u.id),
            email=u.email,
            display_name=u.display_name or "",
            role=u.platform_role,
            is_active=u.is_active,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            allowed_models=allowed_models,
            allowed_skills=allowed_skills,
        ))

    return UserListResponse(users=users, total=total, page=page, page_size=page_size)
