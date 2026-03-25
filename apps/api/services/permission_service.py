from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import load_settings
from ..core.database import ModelPermissionModel, SkillAssignmentModel, UserModel
from ..core.redis_client import cache_delete, cache_get, cache_set
from ..models.domain import UserPermissions

_settings = load_settings()


async def resolve_user_permissions(user_id: str, db: AsyncSession) -> UserPermissions:
    cache_key = f"perm:{user_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return UserPermissions(
            user_id=cached["user_id"],
            allowed_models=cached["allowed_models"],
            allowed_skills=cached["allowed_skills"],
        )

    now = datetime.now(timezone.utc)

    model_result = await db.execute(
        select(ModelPermissionModel.model_id).where(
            ModelPermissionModel.user_id == user_id,
            ModelPermissionModel.is_active == True,
            (ModelPermissionModel.expires_at == None) | (ModelPermissionModel.expires_at > now),
        )
    )
    allowed_models = [row[0] for row in model_result.all()]

    skill_result = await db.execute(
        select(SkillAssignmentModel.skill_id).where(
            SkillAssignmentModel.user_id == user_id,
            SkillAssignmentModel.is_active == True,
            (SkillAssignmentModel.expires_at == None) | (SkillAssignmentModel.expires_at > now),
        )
    )
    allowed_skills = [row[0] for row in skill_result.all()]

    perms = UserPermissions(
        user_id=user_id,
        allowed_models=allowed_models,
        allowed_skills=allowed_skills,
    )

    await cache_set(
        cache_key,
        {
            "user_id": user_id,
            "allowed_models": allowed_models,
            "allowed_skills": allowed_skills,
        },
        _settings.redis_perm_ttl,
    )

    return perms


async def check_model_access(user_id: str, model_id: str, db: AsyncSession) -> bool:
    perms = await resolve_user_permissions(user_id, db)
    return model_id in perms.allowed_models


async def check_skill_access(user_id: str, skill_id: str, db: AsyncSession) -> bool:
    perms = await resolve_user_permissions(user_id, db)
    return skill_id in perms.allowed_skills


async def invalidate_user_permissions(user_id: str) -> None:
    await cache_delete(f"perm:{user_id}")
