from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import (
    ModelPermissionModel,
    SkillAssignmentModel,
    UserModel,
    get_session,
)
from ..schemas.api import (
    SkillAssignRequest,
    SkillAssignResponse,
    SkillRevokeRequest,
    SkillRevokeResponse,
    SkillResponse,
    SkillsListResponse,
    SkillAssignmentInfo,
)
from ..services.permission_service import invalidate_user_permissions

logger = logging.getLogger("backend.skills_router")

router = APIRouter(prefix="/skills", tags=["skills"])


# ── Skill definitions (could be in DB; hardcoded for governance clarity) ──

SKILL_REGISTRY = {
    "skill_summarizer": {
        "display_name": "Document Summarizer",
        "description": "Summarizes long documents into key points",
        "required_models": ["claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"],
    },
    "skill_analyst": {
        "display_name": "Data Analyst",
        "description": "Analyzes structured data and provides insights",
        "required_models": ["claude-3-5-sonnet-20241022", "gemini-1.5-pro"],
    },
    "skill_coder": {
        "display_name": "Code Assistant",
        "description": "Generates, reviews, and explains code",
        "required_models": ["claude-3-5-sonnet-20241022", "gpt-4o"],
    },
    "skill_translator": {
        "display_name": "Language Translator",
        "description": "Translates text between languages",
        "required_models": ["claude-3-haiku-20240307", "gemini-1.5-pro"],
    },
}


@router.get("", response_model=SkillsListResponse)
async def list_skills(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user

    if user.role == "admin":
        skills = []
        for skill_id, info in SKILL_REGISTRY.items():
            skills.append(SkillResponse(
                skill_id=skill_id,
                display_name=info["display_name"],
                description=info["description"],
                required_models=info["required_models"],
                is_active=True,
                assignment=None,
            ))
        return SkillsListResponse(skills=skills)

    result = await db.execute(
        select(SkillAssignmentModel).where(
            SkillAssignmentModel.user_id == user.user_id,
            SkillAssignmentModel.is_active == True,
        )
    )
    assignments = {a.skill_id: a for a in result.scalars().all()}

    skills = []
    for skill_id, info in SKILL_REGISTRY.items():
        if skill_id not in assignments:
            continue
        a = assignments[skill_id]
        skills.append(SkillResponse(
            skill_id=skill_id,
            display_name=info["display_name"],
            description=info["description"],
            required_models=info["required_models"],
            is_active=True,
            assignment=SkillAssignmentInfo(
                assigned_at=a.assigned_at.isoformat() if a.assigned_at else "",
                expires_at=a.expires_at.isoformat() if a.expires_at else None,
                is_active=a.is_active,
            ),
        ))

    return SkillsListResponse(skills=skills)


@router.post("/assign", response_model=SkillAssignResponse)
async def assign_skill(
    body: SkillAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": 403, "title": "Access Denied", "detail": "Admin role required"},
        )

    if body.skill_id not in SKILL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail={"status": 400, "title": "Bad Request", "detail": f"Unknown skill: {body.skill_id}"},
        )

    existing = await db.execute(
        select(SkillAssignmentModel).where(
            SkillAssignmentModel.user_id == body.user_id,
            SkillAssignmentModel.skill_id == body.skill_id,
            SkillAssignmentModel.is_active == True,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail={"status": 409, "title": "Conflict", "detail": "Skill already actively assigned to this user"},
        )

    now = datetime.now(timezone.utc)
    expires_at = None
    if body.expires_at:
        expires_at = datetime.fromisoformat(body.expires_at.replace("Z", "+00:00"))

    assignment = SkillAssignmentModel(
        id=str(uuid4()),
        user_id=body.user_id,
        skill_id=body.skill_id,
        assigned_by=user.user_id,
        assigned_at=now,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    await invalidate_user_permissions(body.user_id)

    return SkillAssignResponse(
        assignment_id=str(assignment.id),
        user_id=str(assignment.user_id),
        skill_id=assignment.skill_id,
        assigned_at=assignment.assigned_at.isoformat(),
        expires_at=assignment.expires_at.isoformat() if assignment.expires_at else None,
        assigned_by=str(assignment.assigned_by),
    )


@router.post("/revoke", response_model=SkillRevokeResponse)
async def revoke_skill(
    body: SkillRevokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": 403, "title": "Access Denied", "detail": "Admin role required"},
        )

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
        raise HTTPException(
            status_code=404,
            detail={"status": 404, "title": "Not Found", "detail": "No active assignment found"},
        )

    await invalidate_user_permissions(body.user_id)

    return SkillRevokeResponse(
        revoked=True,
        user_id=body.user_id,
        skill_id=body.skill_id,
        revoked_at=now.isoformat(),
        revoked_by=user.user_id,
    )
