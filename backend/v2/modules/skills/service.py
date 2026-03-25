from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import (
    SkillAssignmentModel,
    SkillExecutionModel,
    SkillModel,
    SkillVersionModel,
    UserModel,
)
from backend.v2.shared.errors import ConflictError, NotFoundError, ValidationError
from backend.v2.shared.logger import get_logger

logger = get_logger("services.skills")


def _skill_to_dict(skill: SkillModel, include_assignment_count: bool = False, assignment_count: int = 0) -> dict:
    """Convert skill model to response dict with BOTH old and new field names for backward compatibility."""
    base = {
        "id": skill.id,
        "skill_id": skill.id,
        "org_id": skill.org_id,
        "name": skill.name,
        "display_name": skill.name,
        "description": skill.description,
        "content": skill.content,
        "instructions": skill.instructions or skill.content,
        "category": skill.category,
        "skill_type": skill.category,
        "domain": skill.domain or "general",
        "status": skill.status,
        "is_enabled": skill.status in ("active", "published"),
        "version": str(skill.version),
        "created_by": skill.created_by,
        "created_at": skill.created_at.isoformat() if skill.created_at else "",
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
        "required_models": skill.required_models or [],
        "input_schema": skill.input_schema or {},
        "output_format": skill.output_format or {},
        "execution_handler": skill.execution_handler or "",
        "error_handling": skill.error_handling or {},
    }
    if include_assignment_count:
        base["assignment_count"] = assignment_count
    return base


class SkillService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_skills(self, org_id: str, page: int = 1, page_size: int = 20, search: str = "", category: str = "", status: str = "", skill_type: str = "", domain: str = "") -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        filters = [SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)]
        if search:
            filters.append(SkillModel.name.ilike(f"%{search}%"))
        if category or skill_type:
            val = category or skill_type
            filters.append(SkillModel.category == val)
        if status:
            filters.append(SkillModel.status == status)
        if domain:
            filters.append(SkillModel.domain == domain)

        count_q = select(func.count()).select_from(SkillModel).where(*filters)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = select(SkillModel).where(*filters).order_by(SkillModel.updated_at.desc()).offset(offset).limit(page_size)
        rows = (await self.db.execute(query)).scalars().all()

        items = [_skill_to_dict(r, include_assignment_count=True, assignment_count=0) for r in rows]
        return items, total

    async def get_skill(self, org_id: str, skill_id: str) -> dict:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError("Skill not found")

        count_q = select(func.count()).select_from(SkillAssignmentModel).where(SkillAssignmentModel.skill_id == skill_id)
        assignment_count = (await self.db.execute(count_q)).scalar() or 0
        return _skill_to_dict(skill, include_assignment_count=True, assignment_count=assignment_count)

    async def create_skill(self, org_id: str, created_by: str, name: str = "", display_name: str = "", description: str = "", content: str = "", instructions: str = "", category: str = "general", skill_type: str = "", domain: str = "general", required_models: list | None = None, input_schema: dict | None = None, output_format: dict | None = None, execution_handler: str = "", error_handling: dict | None = None, is_enabled: bool | None = None) -> dict:
        actual_name = name or display_name
        if not actual_name:
            raise ValidationError("Skill name is required")

        result = await self.db.execute(select(SkillModel).where(SkillModel.org_id == org_id, SkillModel.name == actual_name, SkillModel.deleted_at.is_(None)))
        if result.scalar_one_or_none():
            raise ConflictError("A skill with this name already exists")

        skill_id = str(uuid4())
        now = datetime.now(UTC)
        status = "active" if is_enabled else "draft"
        skill = SkillModel(
            id=skill_id, org_id=org_id, name=actual_name, description=description,
            content=content or instructions, category=category or skill_type or "general",
            status=status, created_by=created_by, version=1, created_at=now, updated_at=now,
            domain=domain, required_models=required_models or [],
            input_schema=input_schema or {}, output_format=output_format or {},
            execution_handler=execution_handler, error_handling=error_handling or {},
            instructions=instructions or content,
        )
        self.db.add(skill)

        version = SkillVersionModel(id=str(uuid4()), skill_id=skill_id, content=content or instructions, version=1, created_by=created_by, created_at=now)
        self.db.add(version)

        await self.db.flush()
        return _skill_to_dict(skill)

    async def update_skill(self, org_id: str, skill_id: str, user_id: str, **kwargs) -> dict:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError("Skill not found")

        name_val = kwargs.get("name") or kwargs.get("display_name")
        if name_val:
            dup = await self.db.execute(select(SkillModel).where(SkillModel.org_id == org_id, SkillModel.name == name_val, SkillModel.id != skill_id, SkillModel.deleted_at.is_(None)))
            if dup.scalar_one_or_none():
                raise ConflictError("A skill with this name already exists")

        for key, value in kwargs.items():
            if value is None:
                continue
            if key == "display_name":
                setattr(skill, "name", value)
            elif key == "skill_type":
                setattr(skill, "category", value)
            elif key == "instructions":
                setattr(skill, "instructions", value)
                if not skill.content:
                    setattr(skill, "content", value)
            elif key == "is_enabled":
                setattr(skill, "status", "active" if value else "draft")
            elif hasattr(skill, key):
                setattr(skill, key, value)
        skill.updated_at = datetime.now(UTC)
        await self.db.flush()
        return _skill_to_dict(skill)

    async def delete_skill(self, org_id: str, skill_id: str) -> None:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError("Skill not found")
        skill.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def toggle_skill_state(self, org_id: str, skill_id: str, is_enabled: bool) -> dict:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError("Skill not found")
        skill.status = "active" if is_enabled else "draft"
        skill.updated_at = datetime.now(UTC)
        await self.db.flush()
        return {"skill_id": skill.id, "is_enabled": is_enabled, "updated_at": skill.updated_at.isoformat()}

    async def assign_skill(self, org_id: str, user_id: str, skill_id: str, assigned_by: str, expires_at: str | None = None) -> dict:
        user_result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
        if not user_result.scalar_one_or_none():
            raise NotFoundError("User not found")
        skill_result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        if not skill_result.scalar_one_or_none():
            raise NotFoundError("Skill not found")

        existing = await self.db.execute(select(SkillAssignmentModel).where(SkillAssignmentModel.skill_id == skill_id, SkillAssignmentModel.assignee_type == "user", SkillAssignmentModel.assignee_id == user_id))
        if existing.scalar_one_or_none():
            raise ConflictError("Skill already assigned to this user")

        now = datetime.now(UTC)
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if expires_at else None
        assignment = SkillAssignmentModel(id=str(uuid4()), skill_id=skill_id, assignee_type="user", assignee_id=user_id, assigned_by=assigned_by, assigned_at=now, expires_at=expires)
        self.db.add(assignment)
        await self.db.flush()
        return {"assignment_id": assignment.id, "user_id": user_id, "skill_id": skill_id, "assigned_at": now.isoformat(), "expires_at": expires.isoformat() if expires else None, "assigned_by": assigned_by}

    async def revoke_skill(self, org_id: str, user_id: str, skill_id: str, revoked_by: str) -> dict:
        result = await self.db.execute(select(SkillAssignmentModel).where(SkillAssignmentModel.skill_id == skill_id, SkillAssignmentModel.assignee_type == "user", SkillAssignmentModel.assignee_id == user_id))
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise NotFoundError("Assignment not found")
        await self.db.delete(assignment)
        await self.db.flush()
        now = datetime.now(UTC)
        return {"revoked": True, "user_id": user_id, "skill_id": skill_id, "revoked_at": now.isoformat(), "revoked_by": revoked_by}

    async def get_versions(self, org_id: str, skill_id: str) -> list[dict]:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        if not result.scalar_one_or_none():
            raise NotFoundError("Skill not found")
        versions = (await self.db.execute(select(SkillVersionModel).where(SkillVersionModel.skill_id == skill_id).order_by(SkillVersionModel.version.desc()))).scalars().all()
        return [{"id": v.id, "skill_id": v.skill_id, "content": v.content, "version": v.version, "created_by": v.created_by, "created_at": v.created_at.isoformat() if v.created_at else ""} for v in versions]

    async def publish_skill(self, org_id: str, skill_id: str, user_id: str) -> dict:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError("Skill not found")

        new_version = skill.version + 1
        version = SkillVersionModel(id=str(uuid4()), skill_id=skill_id, content=skill.content, version=new_version, created_by=user_id, created_at=datetime.now(UTC))
        self.db.add(version)

        skill.status = "active"
        skill.version = new_version
        skill.updated_at = datetime.now(UTC)
        await self.db.flush()
        return {"id": skill.id, "status": skill.status, "version": skill.version}

    async def duplicate_skill(self, org_id: str, skill_id: str, user_id: str) -> dict:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("Skill not found")

        new_id = str(uuid4())
        now = datetime.now(UTC)
        new_skill = SkillModel(
            id=new_id, org_id=org_id, name=f"{source.name} (Copy)", description=source.description,
            content=source.content, category=source.category, status="draft", created_by=user_id,
            version=1, created_at=now, updated_at=now, domain=source.domain,
            required_models=source.required_models, input_schema=source.input_schema,
            output_format=source.output_format, execution_handler=source.execution_handler,
            error_handling=source.error_handling, instructions=source.instructions,
        )
        self.db.add(new_skill)

        version = SkillVersionModel(id=str(uuid4()), skill_id=new_id, content=source.content, version=1, created_by=user_id, created_at=now)
        self.db.add(version)

        await self.db.flush()
        return _skill_to_dict(new_skill)

    async def get_assignments(self, org_id: str, skill_id: str) -> list[dict]:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        if not result.scalar_one_or_none():
            raise NotFoundError("Skill not found")
        assignments = (await self.db.execute(select(SkillAssignmentModel).where(SkillAssignmentModel.skill_id == skill_id).order_by(SkillAssignmentModel.assigned_at.desc()))).scalars().all()
        return [{"id": a.id, "skill_id": a.skill_id, "assignee_type": a.assignee_type, "assignee_id": a.assignee_id, "assigned_by": a.assigned_by, "assigned_at": a.assigned_at.isoformat() if a.assigned_at else "", "expires_at": a.expires_at.isoformat() if a.expires_at else None} for a in assignments]

    async def test_skill(self, org_id: str, skill_id: str, user_id: str, input_data: dict) -> dict:
        result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        skill = result.scalar_one_or_none()
        if not skill:
            raise NotFoundError("Skill not found")

        start = time.monotonic()
        execution_id = str(uuid4())
        execution = SkillExecutionModel(id=execution_id, skill_id=skill_id, user_id=user_id, status="completed", input_data=input_data, output_data={"result": f"Preview execution of skill '{skill.name}'", "skill_content": skill.content}, duration_ms=0, created_at=datetime.now(UTC))
        self.db.add(execution)
        await self.db.flush()

        duration_ms = int((time.monotonic() - start) * 1000)
        execution.duration_ms = duration_ms
        await self.db.flush()

        return {"id": execution.id, "skill_id": skill_id, "user_id": user_id, "status": "completed", "output_data": execution.output_data, "duration_ms": duration_ms, "created_at": execution.created_at.isoformat()}
