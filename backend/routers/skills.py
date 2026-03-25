from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import (
    SkillAssignmentModel,
    get_session,
)
from ..schemas.api import (
    SkillAssignRequest,
    SkillAssignResponse,
    SkillCreateRequest,
    SkillDeleteResponse,
    SkillFullResponse,
    SkillRevokeRequest,
    SkillRevokeResponse,
    SkillsPaginatedResponse,
    SkillStateUpdateRequest,
    SkillStateUpdateResponse,
    SkillUpdateRequest,
)
from ..services.permission_service import invalidate_user_permissions
from ..services.skill_registry import (
    create_skill_db,
    delete_skill_db,
    get_skill_assignment_count,
    get_skill_db,
    list_skills_db,
    list_skills_paginated,
    set_skill_enabled_db,
    update_skill_db,
)

logger = logging.getLogger("backend.skills_router")

router = APIRouter(prefix="/skills", tags=["skills"])


def _is_admin(role: str) -> bool:
    return role in {"ORG_ADMIN", "SECURITY_ADMIN"}


def _skill_to_full(skill, count: int = 0) -> SkillFullResponse:
    return SkillFullResponse(
        skill_id=skill.skill_id,
        display_name=skill.display_name,
        description=skill.description,
        skill_type=skill.skill_type,
        domain=skill.domain,
        required_models=skill.required_models,
        is_enabled=skill.is_enabled,
        version=skill.version,
        input_schema=skill.input_schema,
        output_format=skill.output_format,
        execution_handler=skill.execution_handler,
        error_handling=skill.error_handling,
        instructions=skill.instructions,
        assignment_count=count,
    )


@router.get("", response_model=SkillsPaginatedResponse)
async def list_skills_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    skill_type: str = Query(""),
    domain: str = Query(""),
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user

    if _is_admin(user.role):
        skills, total, total_pages = await list_skills_paginated(
            db, page=page, page_size=page_size,
            search=search, skill_type=skill_type, domain=domain,
            include_disabled=True,
        )
        items = []
        for s in skills:
            c = await get_skill_assignment_count(db, s.skill_id)
            items.append(_skill_to_full(s, c))
        return SkillsPaginatedResponse(
            skills=items, total=total, page=page, page_size=page_size, total_pages=total_pages,
        )

    result = await db.execute(
        select(SkillAssignmentModel).where(
            SkillAssignmentModel.user_id == user.user_id,
            SkillAssignmentModel.is_active == True,
        )
    )
    assignments = {a.skill_id: a for a in result.scalars().all()}
    items = []
    for s in await list_skills_db(db, include_disabled=False):
        if s.skill_id in assignments:
            items.append(_skill_to_full(s))
    return SkillsPaginatedResponse(
        skills=items, total=len(items), page=1, page_size=len(items), total_pages=1,
    )


@router.get("/registry")
async def list_skill_registry(request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    items = []
    for s in await list_skills_db(db, include_disabled=True):
        c = await get_skill_assignment_count(db, s.skill_id)
        items.append(_skill_to_full(s, c))
    return {"skills": items, "total": len(items)}


@router.post("", response_model=SkillFullResponse)
async def create_skill(body: SkillCreateRequest, request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    try:
        skill = await create_skill_db(db, body.model_dump(), user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _skill_to_full(skill)


@router.get("/{skill_id}", response_model=SkillFullResponse)
async def get_skill(skill_id: str, request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    skill = await get_skill_db(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    c = await get_skill_assignment_count(db, skill_id)
    return _skill_to_full(skill, c)


@router.put("/{skill_id}", response_model=SkillFullResponse)
async def update_skill(skill_id: str, body: SkillUpdateRequest, request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    skill = await update_skill_db(db, skill_id, data, user.user_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    c = await get_skill_assignment_count(db, skill_id)
    return _skill_to_full(skill, c)


@router.delete("/{skill_id}", response_model=SkillDeleteResponse)
async def delete_skill(skill_id: str, request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    deleted = await delete_skill_db(db, skill_id, user.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_id}")
    return SkillDeleteResponse(deleted=True, skill_id=skill_id, message=f"Skill '{skill_id}' deleted successfully")


@router.patch("/{skill_id}/state", response_model=SkillStateUpdateResponse)
async def update_skill_state(skill_id: str, body: SkillStateUpdateRequest, request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    updated = await set_skill_enabled_db(db, skill_id, body.is_enabled, user.user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Unknown skill: {skill_id}")
    return SkillStateUpdateResponse(skill_id=updated.skill_id, is_enabled=updated.is_enabled, updated_at=datetime.now(timezone.utc).isoformat())


@router.post("/assign", response_model=SkillAssignResponse)
async def assign_skill(body: SkillAssignRequest, request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    skill = await get_skill_db(db, body.skill_id)
    if skill is None:
        raise HTTPException(status_code=400, detail=f"Unknown skill: {body.skill_id}")
    if not skill.is_enabled:
        raise HTTPException(status_code=409, detail=f"Skill disabled: {body.skill_id}")
    existing = await db.execute(
        select(SkillAssignmentModel).where(
            SkillAssignmentModel.user_id == body.user_id,
            SkillAssignmentModel.skill_id == body.skill_id,
            SkillAssignmentModel.is_active == True,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Skill already actively assigned")
    now = datetime.now(timezone.utc)
    expires_at = None
    if body.expires_at:
        expires_at = datetime.fromisoformat(body.expires_at.replace("Z", "+00:00"))
    assignment = SkillAssignmentModel(
        id=str(uuid4()), user_id=body.user_id, skill_id=body.skill_id,
        assigned_by=user.user_id, assigned_at=now, expires_at=expires_at, is_active=True,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    await invalidate_user_permissions(body.user_id)
    return SkillAssignResponse(
        assignment_id=str(assignment.id), user_id=str(assignment.user_id),
        skill_id=assignment.skill_id, assigned_at=assignment.assigned_at.isoformat(),
        expires_at=assignment.expires_at.isoformat() if assignment.expires_at else None,
        assigned_by=str(assignment.assigned_by),
    )


@router.post("/revoke", response_model=SkillRevokeResponse)
async def revoke_skill(body: SkillRevokeRequest, request: Request, db: AsyncSession = Depends(get_session)):
    user = request.state.user
    if not _is_admin(user.role):
        raise HTTPException(status_code=403, detail="Admin role required")
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(SkillAssignmentModel)
        .where(
            SkillAssignmentModel.user_id == body.user_id,
            SkillAssignmentModel.skill_id == body.skill_id,
            SkillAssignmentModel.is_active == True,
        )
        .values(is_active=False, revoked_by=user.user_id, revoked_at=now)
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="No active assignment found")
    await invalidate_user_permissions(body.user_id)
    return SkillRevokeResponse(
        revoked=True, user_id=body.user_id, skill_id=body.skill_id,
        revoked_at=now.isoformat(), revoked_by=user.user_id,
    )
