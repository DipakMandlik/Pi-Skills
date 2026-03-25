from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import (
    InvitationModel,
    SkillAssignmentModel,
    SkillModel,
    UserModel,
)
from backend.v2.shared.errors import ConflictError, NotFoundError, ValidationError
from backend.v2.shared.logger import get_logger

logger = get_logger("services.users")


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self, org_id: str, page: int = 1, page_size: int = 20, search: str = "", role: str = "", status: str = "") -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        filters = [UserModel.org_id == org_id]
        if search:
            filters.append(UserModel.name.ilike(f"%{search}%"))
        if role:
            filters.append(UserModel.role == role)
        if status:
            filters.append(UserModel.status == status)

        count_q = select(func.count()).select_from(UserModel).where(*filters)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = select(UserModel).where(*filters).order_by(UserModel.created_at.desc()).offset(offset).limit(page_size)
        rows = (await self.db.execute(query)).scalars().all()

        items = [
            {
                "id": r.id,
                "user_id": r.id,
                "org_id": r.org_id,
                "email": r.email,
                "name": r.name,
                "display_name": r.name,
                "role": r.role,
                "status": r.status,
                "is_active": r.status == "active",
                "last_active": r.last_active.isoformat() if r.last_active else None,
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
        return items, total

    async def get_user(self, org_id: str, user_id: str) -> dict:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")
        return {
            "id": user.id,
            "user_id": user.id,
            "org_id": user.org_id,
            "email": user.email,
            "name": user.name,
            "display_name": user.name,
            "role": user.role,
            "status": user.status,
            "is_active": user.status == "active",
            "last_active": user.last_active.isoformat() if user.last_active else None,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    async def update_user(self, org_id: str, user_id: str, **kwargs) -> dict:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")

        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.now(UTC)
        await self.db.flush()
        return {
            "id": user.id,
            "user_id": user.id,
            "org_id": user.org_id,
            "email": user.email,
            "name": user.name,
            "display_name": user.name,
            "role": user.role,
            "status": user.status,
            "is_active": user.status == "active",
            "last_active": user.last_active.isoformat() if user.last_active else None,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    async def delete_user(self, org_id: str, user_id: str) -> None:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")
        await self.db.delete(user)
        await self.db.flush()

    async def get_user_skills(self, org_id: str, user_id: str) -> list[dict]:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("User not found")

        assignments = (
            await self.db.execute(
                select(SkillAssignmentModel, SkillModel)
                .join(SkillModel, SkillAssignmentModel.skill_id == SkillModel.id)
                .where(
                    SkillAssignmentModel.assignee_type == "user",
                    SkillAssignmentModel.assignee_id == user_id,
                    SkillModel.org_id == org_id,
                    SkillModel.deleted_at.is_(None),
                )
                .order_by(SkillAssignmentModel.assigned_at.desc())
            )
        ).all()

        return [
            {
                "id": skill.id,
                "name": skill.name,
                "category": skill.category,
                "status": skill.status,
                "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else "",
            }
            for assignment, skill in assignments
        ]

    async def assign_skills(self, org_id: str, user_id: str, skill_ids: list[str], assigned_by: str) -> list[dict]:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("User not found")

        assigned = []
        for skill_id in skill_ids:
            skill_result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
            skill = skill_result.scalar_one_or_none()
            if not skill:
                raise NotFoundError(f"Skill {skill_id} not found")

            existing = await self.db.execute(
                select(SkillAssignmentModel).where(
                    SkillAssignmentModel.skill_id == skill_id,
                    SkillAssignmentModel.assignee_type == "user",
                    SkillAssignmentModel.assignee_id == user_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Skill {skill.name} is already assigned to this user")

            assignment = SkillAssignmentModel(
                id=str(uuid4()),
                skill_id=skill_id,
                assignee_type="user",
                assignee_id=user_id,
                assigned_by=assigned_by,
                assigned_at=datetime.now(UTC),
            )
            self.db.add(assignment)
            assigned.append({"id": assignment.id, "skill_id": skill_id, "skill_name": skill.name})

        await self.db.flush()
        return assigned

    async def remove_skill(self, org_id: str, user_id: str, skill_id: str) -> None:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("User not found")

        assignment_result = await self.db.execute(
            select(SkillAssignmentModel).where(
                SkillAssignmentModel.skill_id == skill_id,
                SkillAssignmentModel.assignee_type == "user",
                SkillAssignmentModel.assignee_id == user_id,
            )
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            raise NotFoundError("Skill assignment not found")

        await self.db.delete(assignment)
        await self.db.flush()

    async def invite_by_email(self, org_id: str, email: str, role: str, invited_by: str) -> dict:
        existing_user = await self.db.execute(select(UserModel).where(UserModel.org_id == org_id, UserModel.email == email.lower()))
        if existing_user.scalar_one_or_none():
            raise ConflictError("User with this email already exists in the organization")

        token = str(uuid4())
        expires_at = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        expires_at = expires_at + timedelta(days=7)

        invitation = InvitationModel(
            id=str(uuid4()),
            org_id=org_id,
            email=email.lower(),
            role=role,
            token=token,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.flush()

        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role,
            "expires_at": invitation.expires_at.isoformat(),
        }
