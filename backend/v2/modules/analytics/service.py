from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.database.client import (
    AuditLogModel,
    SkillExecutionModel,
    SkillModel,
    UserModel,
)
from backend.v2.shared.errors import NotFoundError
from backend.v2.shared.logger import get_logger

logger = get_logger("services.analytics")


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_skill_usage(self, org_id: str, limit: int = 10) -> list[dict]:
        skills = (
            await self.db.execute(
                select(SkillModel, func.count(SkillExecutionModel.id).label("execution_count"))
                .join(SkillExecutionModel, SkillModel.id == SkillExecutionModel.skill_id, isouter=True)
                .where(SkillModel.org_id == org_id, SkillModel.deleted_at.is_(None))
                .group_by(SkillModel.id)
                .order_by(func.count(SkillExecutionModel.id).desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "skill_id": s.id,
                "skill_name": s.name,
                "execution_count": ec or 0,
            }
            for s, ec in skills
        ]

    async def get_skill_errors(self, org_id: str, limit: int = 20) -> list[dict]:
        errors = (
            await self.db.execute(
                select(
                    SkillExecutionModel.skill_id,
                    SkillExecutionModel.error,
                    func.count(SkillExecutionModel.id).label("error_count"),
                    func.max(SkillExecutionModel.created_at).label("last_occurrence"),
                )
                .join(SkillModel, SkillExecutionModel.skill_id == SkillModel.id)
                .where(
                    SkillModel.org_id == org_id,
                    SkillExecutionModel.status == "error",
                    SkillExecutionModel.error.isnot(None),
                )
                .group_by(SkillExecutionModel.skill_id, SkillExecutionModel.error)
                .order_by(func.count(SkillExecutionModel.id).desc())
                .limit(limit)
            )
        ).all()

        skill_names = {}
        for row in errors:
            if row.skill_id not in skill_names:
                skill_result = await self.db.execute(select(SkillModel).where(SkillModel.id == row.skill_id))
                skill = skill_result.scalar_one_or_none()
                skill_names[row.skill_id] = skill.name if skill else "Unknown"

        return [
            {
                "skill_id": e.skill_id,
                "skill_name": skill_names.get(e.skill_id, "Unknown"),
                "error": e.error,
                "count": e.error_count,
                "last_occurrence": e.last_occurrence.isoformat() if e.last_occurrence else "",
            }
            for e in errors
        ]

    async def get_user_activity(self, org_id: str, limit: int = 20) -> list[dict]:
        users = (
            await self.db.execute(
                select(
                    UserModel.id,
                    UserModel.name,
                    func.count(SkillExecutionModel.id).label("execution_count"),
                    func.max(SkillExecutionModel.created_at).label("last_active"),
                )
                .join(SkillExecutionModel, UserModel.id == SkillExecutionModel.user_id, isouter=True)
                .where(UserModel.org_id == org_id)
                .group_by(UserModel.id, UserModel.name)
                .order_by(func.count(SkillExecutionModel.id).desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "user_id": u.id,
                "user_name": u.name,
                "execution_count": ec or 0,
                "last_active": la.isoformat() if la else None,
            }
            for u, ec, la in users
        ]

    async def get_trends(self, org_id: str, days: int = 30) -> list[dict]:
        start_date = datetime.now(UTC) - timedelta(days=days)

        executions = (
            await self.db.execute(
                select(
                    func.date(SkillExecutionModel.created_at).label("date"),
                    func.count(SkillExecutionModel.id).label("count"),
                )
                .join(SkillModel, SkillExecutionModel.skill_id == SkillModel.id)
                .where(SkillModel.org_id == org_id, SkillExecutionModel.created_at >= start_date)
                .group_by(func.date(SkillExecutionModel.created_at))
                .order_by(func.date(SkillExecutionModel.created_at))
            )
        ).all()

        trends = []
        current = start_date.date()
        end = datetime.now(UTC).date()
        exec_map = {str(e.date): e.count for e in executions}

        while current <= end:
            date_str = current.isoformat()
            trends.append({"date": date_str, "value": exec_map.get(date_str, 0)})
            current += timedelta(days=1)

        return trends
