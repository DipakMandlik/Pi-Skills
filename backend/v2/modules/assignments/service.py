from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import (
    SkillAssignmentModel,
    SkillModel,
    TeamModel,
    UserModel,
)
from backend.v2.shared.errors import ConflictError, NotFoundError, ValidationError
from backend.v2.shared.logger import get_logger

logger = get_logger("services.assignments")


class AssignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_assignment(self, org_id: str, assigned_by: str, skill_id: str, assignee_type: str, assignee_id: str, expires_at: str | None = None) -> dict:
        skill_result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
        skill = skill_result.scalar_one_or_none()
        if not skill:
            raise NotFoundError("Skill not found")

        if assignee_type == "user":
            assignee_result = await self.db.execute(select(UserModel).where(UserModel.id == assignee_id, UserModel.org_id == org_id))
            if not assignee_result.scalar_one_or_none():
                raise NotFoundError("User not found in organization")
        elif assignee_type == "team":
            assignee_result = await self.db.execute(select(TeamModel).where(TeamModel.id == assignee_id, TeamModel.org_id == org_id))
            if not assignee_result.scalar_one_or_none():
                raise NotFoundError("Team not found in organization")
        else:
            raise ValidationError("Invalid assignee type. Must be 'user' or 'team'")

        existing = await self.db.execute(
            select(SkillAssignmentModel).where(
                SkillAssignmentModel.skill_id == skill_id,
                SkillAssignmentModel.assignee_type == assignee_type,
                SkillAssignmentModel.assignee_id == assignee_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("This skill is already assigned to the specified assignee")

        expires_dt = None
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at)

        assignment = SkillAssignmentModel(
            id=str(uuid4()),
            skill_id=skill_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            assigned_by=assigned_by,
            assigned_at=datetime.now(UTC),
            expires_at=expires_dt,
        )
        self.db.add(assignment)
        await self.db.flush()

        return {
            "id": assignment.id,
            "skill_id": assignment.skill_id,
            "skill_name": skill.name,
            "assignee_type": assignment.assignee_type,
            "assignee_id": assignment.assignee_id,
            "assigned_by": assignment.assigned_by,
            "assigned_at": assignment.assigned_at.isoformat(),
            "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None,
        }

    async def delete_assignment(self, org_id: str, assignment_id: str) -> None:
        result = await self.db.execute(
            select(SkillAssignmentModel).join(SkillModel, SkillAssignmentModel.skill_id == SkillModel.id).where(
                SkillAssignmentModel.id == assignment_id,
                SkillModel.org_id == org_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise NotFoundError("Assignment not found")

        await self.db.delete(assignment)
        await self.db.flush()

    async def list_assignments(self, org_id: str, page: int = 1, page_size: int = 20, skill_id: str = "", assignee_type: str = "", assignee_id: str = "") -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        filters = [SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)]
        if skill_id:
            filters.append(SkillAssignmentModel.skill_id == skill_id)
        if assignee_type:
            filters.append(SkillAssignmentModel.assignee_type == assignee_type)
        if assignee_id:
            filters.append(SkillAssignmentModel.assignee_id == assignee_id)

        count_q = select(func.count()).select_from(SkillAssignmentModel).join(SkillModel, SkillAssignmentModel.skill_id == SkillModel.id).where(*filters)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            select(SkillAssignmentModel, SkillModel)
            .join(SkillModel, SkillAssignmentModel.skill_id == SkillModel.id)
            .where(*filters)
            .order_by(SkillAssignmentModel.assigned_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.db.execute(query)).all()

        items = [
            {
                "id": a.id,
                "skill_id": a.skill_id,
                "skill_name": s.name,
                "assignee_type": a.assignee_type,
                "assignee_id": a.assignee_id,
                "assigned_by": a.assigned_by,
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else "",
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
            for a, s in rows
        ]
        return items, total
