from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import get_session
from backend.v2.middleware.auth import get_current_user, AuthContext
from backend.v2.modules.skills.service import SkillService
from backend.v2.modules.users.service import UserService
from backend.v2.shared.errors import NotFoundError

router = APIRouter(tags=["skills-v1-compat"])


class V1SkillCreate(BaseModel):
    skill_id: str = ""
    display_name: str
    description: str = ""
    skill_type: str = "ai"
    domain: str = "general"
    required_models: list[str] = []
    input_schema: dict = {}
    output_format: dict = {}
    execution_handler: str = ""
    error_handling: dict = {}
    instructions: str = ""
    is_enabled: bool = True


class V1ToggleState(BaseModel):
    is_enabled: bool


class V1AssignSkill(BaseModel):
    user_id: str
    skill_id: str
    expires_at: str | None = None


class V1RevokeSkill(BaseModel):
    user_id: str
    skill_id: str


def _get_skill_service(db: AsyncSession) -> SkillService:
    return SkillService(db)


def _get_user_service(db: AsyncSession) -> UserService:
    return UserService(db)


@router.get("/skills")
async def list_skills_v1(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    skill_type: str = Query(""),
    domain: str = Query(""),
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_skill_service(db)
    items, total = await service.list_skills(ctx.org_id, page, page_size, search, "", "", skill_type, domain)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return JSONResponse(content={
        "skills": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/skills/{skill_id}")
async def get_skill_v1(skill_id: str, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_skill_service(db)
    result = await service.get_skill(ctx.org_id, skill_id)
    return JSONResponse(content=result)


@router.post("/skills")
async def create_skill_v1(body: V1SkillCreate, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_skill_service(db)
    result = await service.create_skill(
        ctx.org_id, ctx.user_id,
        name=body.skill_id or body.display_name,
        display_name=body.display_name,
        description=body.description,
        content=body.instructions,
        instructions=body.instructions,
        category=body.skill_type,
        skill_type=body.skill_type,
        domain=body.domain,
        required_models=body.required_models,
        input_schema=body.input_schema,
        output_format=body.output_format,
        execution_handler=body.execution_handler,
        error_handling=body.error_handling,
        is_enabled=body.is_enabled,
    )
    return JSONResponse(status_code=201, content=result)


@router.put("/skills/{skill_id}")
async def update_skill_v1(skill_id: str, body: dict, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_skill_service(db)
    result = await service.update_skill(ctx.org_id, skill_id, ctx.user_id, **body)
    return JSONResponse(content=result)


@router.delete("/skills/{skill_id}")
async def delete_skill_v1(skill_id: str, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_skill_service(db)
    await service.delete_skill(ctx.org_id, skill_id)
    return JSONResponse(content={"deleted": True, "skill_id": skill_id, "message": "Skill deleted"})


@router.patch("/skills/{skill_id}/state")
async def toggle_skill_v1(skill_id: str, body: V1ToggleState, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_skill_service(db)
    result = await service.toggle_skill_state(ctx.org_id, skill_id, body.is_enabled)
    return JSONResponse(content=result)


@router.post("/skills/assign")
async def assign_skill_v1(body: V1AssignSkill, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_skill_service(db)
    result = await service.assign_skill(ctx.org_id, body.user_id, body.skill_id, ctx.user_id, body.expires_at)
    return JSONResponse(status_code=201, content=result)


@router.post("/skills/revoke")
async def revoke_skill_v1(body: V1RevokeSkill, ctx: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    service = _get_skill_service(db)
    result = await service.revoke_skill(ctx.org_id, body.user_id, body.skill_id, ctx.user_id)
    return JSONResponse(content=result)


@router.get("/users")
async def list_users_v1(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = _get_user_service(db)
    items, total = await service.list_users(ctx.org_id, page, page_size)
    return JSONResponse(content={
        "users": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })
