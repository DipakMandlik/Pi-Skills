from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import AuthContext, get_current_user
from backend.v2.modules.assignments.schemas import AssignmentCreateRequest
from backend.v2.modules.assignments.service import AssignmentService
from backend.v2.shared.response import created_response, no_content_response, success_response

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


def _get_assignment_service(db: AsyncSession) -> AssignmentService:
    return AssignmentService(db)


@router.get("")
async def list_assignments(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skill_id: str = Query(""),
    assignee_type: str = Query(""),
    assignee_id: str = Query(""),
):
    service = _get_assignment_service(db)
    items, total = await service.list_assignments(ctx.org_id, page, page_size, skill_id, assignee_type, assignee_id)
    return success_response(
        items,
        {"page": page, "total": total, "per_page": page_size, "total_pages": math.ceil(total / page_size) if total > 0 else 0},
    )


@router.post("")
async def create_assignment(
    body: AssignmentCreateRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_assignment_service(db)
    result = await service.create_assignment(
        ctx.org_id,
        ctx.user_id,
        body.skill_id,
        body.assignee_type,
        body.assignee_id,
        body.expires_at,
    )
    return created_response(result)


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_assignment_service(db)
    await service.delete_assignment(ctx.org_id, assignment_id)
    return no_content_response()
