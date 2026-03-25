from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import (
    SkillAssignmentModel,
    SkillModel,
    TeamMemberModel,
    TeamModel,
    UserModel,
)
from backend.v2.shared.errors import ConflictError, NotFoundError, ValidationError
from backend.v2.shared.logger import get_logger

logger = get_logger("services.teams")


class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_teams(self, org_id: str, page: int = 1, page_size: int = 20, search: str = "") -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        filters = [TeamModel.org_id == org_id]
        if search:
            filters.append(TeamModel.name.ilike(f"%{search}%"))

        count_q = select(func.count()).select_from(TeamModel).where(*filters)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = select(TeamModel).where(*filters).order_by(TeamModel.created_at.desc()).offset(offset).limit(page_size)
        rows = (await self.db.execute(query)).scalars().all()

        items = []
        for r in rows:
            member_count_q = select(func.count()).select_from(TeamMemberModel).where(TeamMemberModel.team_id == r.id)
            member_count = (await self.db.execute(member_count_q)).scalar() or 0
            items.append(
                {
                    "id": r.id,
                    "org_id": r.org_id,
                    "name": r.name,
                    "description": r.description,
                    "member_count": member_count,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
            )
        return items, total

    async def create_team(self, org_id: str, name: str, description: str = "") -> dict:
        result = await self.db.execute(select(TeamModel).where(TeamModel.org_id == org_id, TeamModel.name == name))
        if result.scalar_one_or_none():
            raise ConflictError("A team with this name already exists")

        team_id = str(uuid4())
        now = datetime.now(UTC)
        team = TeamModel(id=team_id, org_id=org_id, name=name, description=description, created_at=now, updated_at=now)
        self.db.add(team)
        await self.db.flush()

        return {
            "id": team.id,
            "org_id": team.org_id,
            "name": team.name,
            "description": team.description,
            "member_count": 0,
            "created_at": team.created_at.isoformat(),
            "updated_at": None,
        }

    async def get_team(self, org_id: str, team_id: str) -> dict:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        team = result.scalar_one_or_none()
        if not team:
            raise NotFoundError("Team not found")

        member_count_q = select(func.count()).select_from(TeamMemberModel).where(TeamMemberModel.team_id == team.id)
        member_count = (await self.db.execute(member_count_q)).scalar() or 0

        return {
            "id": team.id,
            "org_id": team.org_id,
            "name": team.name,
            "description": team.description,
            "member_count": member_count,
            "created_at": team.created_at.isoformat() if team.created_at else "",
            "updated_at": team.updated_at.isoformat() if team.updated_at else None,
        }

    async def update_team(self, org_id: str, team_id: str, **kwargs) -> dict:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        team = result.scalar_one_or_none()
        if not team:
            raise NotFoundError("Team not found")

        if "name" in kwargs and kwargs["name"]:
            dup = await self.db.execute(select(TeamModel).where(TeamModel.org_id == org_id, TeamModel.name == kwargs["name"], TeamModel.id != team_id))
            if dup.scalar_one_or_none():
                raise ConflictError("A team with this name already exists")

        for key, value in kwargs.items():
            if value is not None and hasattr(team, key):
                setattr(team, key, value)
        team.updated_at = datetime.now(UTC)
        await self.db.flush()

        member_count_q = select(func.count()).select_from(TeamMemberModel).where(TeamMemberModel.team_id == team.id)
        member_count = (await self.db.execute(member_count_q)).scalar() or 0

        return {
            "id": team.id,
            "org_id": team.org_id,
            "name": team.name,
            "description": team.description,
            "member_count": member_count,
            "created_at": team.created_at.isoformat() if team.created_at else "",
            "updated_at": team.updated_at.isoformat() if team.updated_at else None,
        }

    async def delete_team(self, org_id: str, team_id: str) -> None:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        team = result.scalar_one_or_none()
        if not team:
            raise NotFoundError("Team not found")
        await self.db.delete(team)
        await self.db.flush()

    async def add_members(self, org_id: str, team_id: str, user_ids: list[str]) -> list[dict]:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("Team not found")

        added = []
        for user_id in user_ids:
            user_result = await self.db.execute(select(UserModel).where(UserModel.id == user_id, UserModel.org_id == org_id))
            user = user_result.scalar_one_or_none()
            if not user:
                raise NotFoundError(f"User {user_id} not found in organization")

            existing = await self.db.execute(
                select(TeamMemberModel).where(TeamMemberModel.team_id == team_id, TeamMemberModel.user_id == user_id)
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"User {user.name} is already a member of this team")

            member = TeamMemberModel(
                id=str(uuid4()),
                team_id=team_id,
                user_id=user_id,
                joined_at=datetime.now(UTC),
            )
            self.db.add(member)
            added.append({"id": member.id, "user_id": user_id, "user_name": user.name, "user_email": user.email})

        await self.db.flush()
        return added

    async def remove_member(self, org_id: str, team_id: str, user_id: str) -> None:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("Team not found")

        member_result = await self.db.execute(
            select(TeamMemberModel).where(TeamMemberModel.team_id == team_id, TeamMemberModel.user_id == user_id)
        )
        member = member_result.scalar_one_or_none()
        if not member:
            raise NotFoundError("User is not a member of this team")

        await self.db.delete(member)
        await self.db.flush()

    async def get_members(self, org_id: str, team_id: str) -> list[dict]:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("Team not found")

        members = (
            await self.db.execute(
                select(TeamMemberModel, UserModel)
                .join(UserModel, TeamMemberModel.user_id == UserModel.id)
                .where(TeamMemberModel.team_id == team_id)
                .order_by(TeamMemberModel.joined_at.desc())
            )
        ).all()

        return [
            {
                "id": m.id,
                "user_id": m.user_id,
                "user_name": u.name,
                "user_email": u.email,
                "joined_at": m.joined_at.isoformat() if m.joined_at else "",
            }
            for m, u in members
        ]

    async def get_team_skills(self, org_id: str, team_id: str) -> list[dict]:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("Team not found")

        assignments = (
            await self.db.execute(
                select(SkillAssignmentModel, SkillModel)
                .join(SkillModel, SkillAssignmentModel.skill_id == SkillModel.id)
                .where(
                    SkillAssignmentModel.assignee_type == "team",
                    SkillAssignmentModel.assignee_id == team_id,
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

    async def assign_skills(self, org_id: str, team_id: str, skill_ids: list[str], assigned_by: str) -> list[dict]:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("Team not found")

        assigned = []
        for skill_id in skill_ids:
            skill_result = await self.db.execute(select(SkillModel).where(SkillModel.id == skill_id, SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))
            skill = skill_result.scalar_one_or_none()
            if not skill:
                raise NotFoundError(f"Skill {skill_id} not found")

            existing = await self.db.execute(
                select(SkillAssignmentModel).where(
                    SkillAssignmentModel.skill_id == skill_id,
                    SkillAssignmentModel.assignee_type == "team",
                    SkillAssignmentModel.assignee_id == team_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(f"Skill {skill.name} is already assigned to this team")

            assignment = SkillAssignmentModel(
                id=str(uuid4()),
                skill_id=skill_id,
                assignee_type="team",
                assignee_id=team_id,
                assigned_by=assigned_by,
                assigned_at=datetime.now(UTC),
            )
            self.db.add(assignment)
            assigned.append({"id": assignment.id, "skill_id": skill_id, "skill_name": skill.name})

        await self.db.flush()
        return assigned

    async def remove_skill(self, org_id: str, team_id: str, skill_id: str) -> None:
        result = await self.db.execute(select(TeamModel).where(TeamModel.id == team_id, TeamModel.org_id == org_id))
        if not result.scalar_one_or_none():
            raise NotFoundError("Team not found")

        assignment_result = await self.db.execute(
            select(SkillAssignmentModel).where(
                SkillAssignmentModel.skill_id == skill_id,
                SkillAssignmentModel.assignee_type == "team",
                SkillAssignmentModel.assignee_id == team_id,
            )
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            raise NotFoundError("Skill assignment not found")

        await self.db.delete(assignment)
        await self.db.flush()
