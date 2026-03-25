from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import AuthContext, get_current_user, require_admin
from backend.v2.modules.skills.schemas import (
    SkillCreateRequest,
    SkillExecutionRequest,
    SkillUpdateRequest,
)
from backend.v2.modules.skills.service import SkillService
from backend.v2.shared.errors import ValidationError
from backend.v2.shared.response import created_response, success_response

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillAssignRequest(BaseModel):
    user_id: str
    skill_id: str
    expires_at: str | None = None


class SkillRevokeRequest(BaseModel):
    user_id: str
    skill_id: str


class SkillStateRequest(BaseModel):
    is_enabled: bool


def _get_service(db: AsyncSession) -> SkillService:
    return SkillService(db)


@router.get("")
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    category: str = Query(""),
    skill_type: str = Query(""),
    status: str = Query(""),
    domain: str = Query(""),
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_service(db)
    items, total = await service.list_skills(ctx.org_id, page, page_size, search, category or skill_type, status, skill_type, domain)
    return success_response(items, {"page": page, "total": total, "per_page": page_size, "total_pages": (total + page_size - 1) // page_size if page_size else 0})


@router.get("/{skill_id}")
async def get_skill(skill_id: str, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.get_skill(ctx.org_id, skill_id)
    return success_response(result)


@router.post("")
async def create_skill(body: SkillCreateRequest, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.create_skill(
        ctx.org_id, ctx.user_id,
        name=body.name, display_name=body.display_name if hasattr(body, 'display_name') else "",
        description=body.description, content=body.content,
        instructions=body.instructions if hasattr(body, 'instructions') else "",
        category=body.category, skill_type=body.skill_type if hasattr(body, 'skill_type') else "",
        domain=body.domain if hasattr(body, 'domain') else "general",
        required_models=body.required_models if hasattr(body, 'required_models') else None,
        input_schema=body.input_schema if hasattr(body, 'input_schema') else None,
        output_format=body.output_format if hasattr(body, 'output_format') else None,
        execution_handler=body.execution_handler if hasattr(body, 'execution_handler') else "",
        error_handling=body.error_handling if hasattr(body, 'error_handling') else None,
        is_enabled=body.is_enabled if hasattr(body, 'is_enabled') else None,
    )
    return created_response(result)


@router.put("/{skill_id}")
async def update_skill(skill_id: str, body: dict, ctx: AuthContext = Depends(require_admin), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.update_skill(ctx.org_id, skill_id, ctx.user_id, **body)
    return success_response(result)


@router.patch("/{skill_id}")
async def patch_skill(skill_id: str, body: dict, ctx: AuthContext = Depends(require_admin), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.update_skill(ctx.org_id, skill_id, ctx.user_id, **body)
    return success_response(result)


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, ctx: AuthContext = Depends(require_admin), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    await service.delete_skill(ctx.org_id, skill_id)
    return success_response({"deleted": True, "skill_id": skill_id, "message": "Skill deleted"})


@router.patch("/{skill_id}/state")
async def toggle_skill_state(skill_id: str, body: SkillStateRequest, ctx: AuthContext = Depends(require_admin), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.toggle_skill_state(ctx.org_id, skill_id, body.is_enabled)
    return success_response(result)


@router.post("/assign")
async def assign_skill(body: SkillAssignRequest, ctx: AuthContext = Depends(require_admin), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.assign_skill(ctx.org_id, body.user_id, body.skill_id, ctx.user_id, body.expires_at)
    return created_response(result)


@router.post("/revoke")
async def revoke_skill(body: SkillRevokeRequest, ctx: AuthContext = Depends(require_admin), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.revoke_skill(ctx.org_id, body.user_id, body.skill_id, ctx.user_id)
    return success_response(result)


@router.get("/{skill_id}/versions")
async def get_versions(skill_id: str, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.get_versions(ctx.org_id, skill_id)
    return success_response(result)


@router.post("/{skill_id}/publish")
async def publish_skill(skill_id: str, ctx: AuthContext = Depends(require_admin), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.publish_skill(ctx.org_id, skill_id, ctx.user_id)
    return success_response(result)


@router.post("/{skill_id}/duplicate")
async def duplicate_skill(skill_id: str, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.duplicate_skill(ctx.org_id, skill_id, ctx.user_id)
    return created_response(result)


@router.get("/{skill_id}/assignments")
async def get_assignments(skill_id: str, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.get_assignments(ctx.org_id, skill_id)
    return success_response(result)


@router.post("/{skill_id}/test")
async def test_skill(skill_id: str, body: SkillExecutionRequest, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_service(db)
    result = await service.test_skill(ctx.org_id, skill_id, ctx.user_id, body.input_data)
    return success_response(result)
