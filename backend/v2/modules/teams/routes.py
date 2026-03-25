from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import AuthContext, get_current_user
from backend.v2.modules.teams.schemas import (
    AddMembersRequest,
    AssignSkillsRequest,
    TeamCreateRequest,
    TeamUpdateRequest,
)
from backend.v2.modules.teams.service import TeamService
from backend.v2.shared.response import created_response, no_content_response, success_response

router = APIRouter(prefix="/api/teams", tags=["teams"])


def _get_team_service(db: AsyncSession) -> TeamService:
    return TeamService(db)


@router.get("")
async def list_teams(
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
):
    service = _get_team_service(db)
    items, total = await service.list_teams(ctx.org_id, page, page_size, search)
    return success_response(
        items,
        {"page": page, "total": total, "per_page": page_size, "total_pages": math.ceil(total / page_size) if total > 0 else 0},
    )


@router.post("")
async def create_team(
    body: TeamCreateRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    result = await service.create_team(ctx.org_id, body.name, body.description)
    return created_response(result)


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    result = await service.get_team(ctx.org_id, team_id)
    return success_response(result)


@router.patch("/{team_id}")
async def update_team(
    team_id: str,
    body: TeamUpdateRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    kwargs = body.model_dump(exclude_none=True)
    result = await service.update_team(ctx.org_id, team_id, **kwargs)
    return success_response(result)


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    await service.delete_team(ctx.org_id, team_id)
    return no_content_response()


@router.get("/{team_id}/members")
async def get_team_members(
    team_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    members = await service.get_members(ctx.org_id, team_id)
    return success_response(members)


@router.post("/{team_id}/members")
async def add_members(
    team_id: str,
    body: AddMembersRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    result = await service.add_members(ctx.org_id, team_id, body.user_ids)
    return created_response(result)


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: str,
    user_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    await service.remove_member(ctx.org_id, team_id, user_id)
    return no_content_response()


@router.get("/{team_id}/skills")
async def get_team_skills(
    team_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    skills = await service.get_team_skills(ctx.org_id, team_id)
    return success_response(skills)


@router.post("/{team_id}/skills/assign")
async def assign_skills(
    team_id: str,
    body: AssignSkillsRequest,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    result = await service.assign_skills(ctx.org_id, team_id, body.skill_ids, ctx.user_id)
    return created_response(result)


@router.delete("/{team_id}/skills/{skill_id}")
async def remove_skill(
    team_id: str,
    skill_id: str,
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_team_service(db)
    await service.remove_skill(ctx.org_id, team_id, skill_id)
    return no_content_response()
