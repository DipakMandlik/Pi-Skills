from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import (
    AuditLogModel,
    OrganizationModel,
    SkillAssignmentModel,
    SkillModel,
    TeamModel,
    UserModel,
)
from backend.v2.shared.errors import NotFoundError
from backend.v2.shared.logger import get_logger

logger = get_logger("services.organizations")


class OrgService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_org(self, org_id: str) -> dict:
        result = await self.db.execute(select(OrganizationModel).where(OrganizationModel.id == org_id))
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundError("Organization not found")
        return {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "settings": org.settings or {},
            "created_at": org.created_at.isoformat() if org.created_at else "",
            "updated_at": org.updated_at.isoformat() if org.updated_at else None,
        }

    async def update_org(self, org_id: str, **kwargs) -> dict:
        result = await self.db.execute(select(OrganizationModel).where(OrganizationModel.id == org_id))
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundError("Organization not found")

        for key, value in kwargs.items():
            if value is not None and hasattr(org, key):
                setattr(org, key, value)
        org.updated_at = datetime.now(UTC)
        await self.db.flush()

        return {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "plan": org.plan,
            "settings": org.settings or {},
            "created_at": org.created_at.isoformat() if org.created_at else "",
            "updated_at": org.updated_at.isoformat() if org.updated_at else None,
        }

    async def get_stats(self, org_id: str) -> dict:
        total_users = (await self.db.execute(select(func.count()).select_from(UserModel).where(UserModel.org_id == org_id))).scalar() or 0
        total_teams = (await self.db.execute(select(func.count()).select_from(TeamModel).where(TeamModel.org_id == org_id))).scalar() or 0
        total_skills = (await self.db.execute(select(func.count()).select_from(SkillModel).where(SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None)))).scalar() or 0
        total_assignments = (await self.db.execute(select(func.count()).select_from(SkillAssignmentModel).join(SkillModel, SkillAssignmentModel.skill_id == SkillModel.id).where(SkillModel.org_id == org_id))).scalar() or 0
        active_skills = (await self.db.execute(select(func.count()).select_from(SkillModel).where(SkillModel.org_id == org_id, SkillModel.status == "active", SkillModel.deleted_at.is_(None)))).scalar() or 0
        draft_skills = (await self.db.execute(select(func.count()).select_from(SkillModel).where(SkillModel.org_id == org_id, SkillModel.status == "draft", SkillModel.deleted_at.is_(None)))).scalar() or 0

        return {
            "total_users": total_users,
            "total_teams": total_teams,
            "total_skills": total_skills,
            "total_assignments": total_assignments,
            "active_skills": active_skills,
            "draft_skills": draft_skills,
        }

    async def get_activity(self, org_id: str, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        count_q = select(func.count()).select_from(AuditLogModel).where(AuditLogModel.org_id == org_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        logs = (
            await self.db.execute(
                select(AuditLogModel)
                .where(AuditLogModel.org_id == org_id)
                .order_by(AuditLogModel.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
        ).all()

        return [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "metadata_": log.metadata_ or {},
                "created_at": log.created_at.isoformat() if log.created_at else "",
            }
            for log in logs
        ], total
