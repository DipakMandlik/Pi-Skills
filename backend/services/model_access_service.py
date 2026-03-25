"""
Model Access Service - Validates model access and applies limits
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import ModelAccessControlModel, RegisteredModelModel
from ..core.redis_client import cache_get, cache_set

logger = logging.getLogger("backend.model_access_service")

_CACHE_TTL = 300


class ModelAccessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_model_access(
        self, user_id: str, user_role: str, model_id: str
    ) -> dict:
        cache_key = f"model:access:{model_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            if not cached.get("enabled", False):
                return {
                    "allowed": False,
                    "reason": "MODEL_DISABLED",
                    "message": f"Model '{model_id}' is disabled",
                }
            allowed_roles = cached.get("allowed_roles", [])
            if allowed_roles and user_role not in allowed_roles:
                return {
                    "allowed": False,
                    "reason": "ROLE_NOT_ALLOWED",
                    "message": f"Role '{user_role}' not allowed for model '{model_id}'",
                }
            return {
                "allowed": True,
                "max_tokens_per_request": cached.get("max_tokens_per_request", 4096),
                "rate_limit": cached.get("rate_limit_per_minute", 60),
            }

        result = await self.db.execute(
            select(ModelAccessControlModel).where(
                ModelAccessControlModel.model_id == model_id
            )
        )
        access_ctrl = result.scalar_one_or_none()

        if access_ctrl is None:
            model_check = await self.db.execute(
                select(RegisteredModelModel).where(
                    RegisteredModelModel.model_id == model_id,
                    RegisteredModelModel.is_available == True,
                )
            )
            if model_check.scalar_one_or_none() is None:
                return {
                    "allowed": False,
                    "reason": "MODEL_NOT_FOUND",
                    "message": f"Model '{model_id}' not found or unavailable",
                }
            return {"allowed": True, "max_tokens_per_request": 4096, "rate_limit": 60}

        if not access_ctrl.enabled:
            await cache_set(
                cache_key,
                {"enabled": False, "allowed_roles": [], "max_tokens_per_request": 0, "rate_limit_per_minute": 0},
                _CACHE_TTL,
            )
            return {
                "allowed": False,
                "reason": "MODEL_DISABLED",
                "message": f"Model '{model_id}' is disabled",
            }

        allowed_roles = access_ctrl.allowed_roles or []
        if allowed_roles and user_role not in allowed_roles:
            return {
                "allowed": False,
                "reason": "ROLE_NOT_ALLOWED",
                "message": f"Role '{user_role}' not allowed for model '{model_id}'",
            }

        await cache_set(
            cache_key,
            {
                "enabled": access_ctrl.enabled,
                "allowed_roles": allowed_roles,
                "max_tokens_per_request": access_ctrl.max_tokens_per_request,
                "rate_limit_per_minute": access_ctrl.rate_limit_per_minute,
            },
            _CACHE_TTL,
        )

        return {
            "allowed": True,
            "max_tokens_per_request": access_ctrl.max_tokens_per_request,
            "rate_limit": access_ctrl.rate_limit_per_minute,
        }

    async def set_model_access(
        self,
        model_id: str,
        allowed_roles: list[str],
        max_tokens_per_request: int = 4096,
        enabled: bool = True,
        rate_limit_per_minute: int = 60,
    ) -> dict:
        result = await self.db.execute(
            select(ModelAccessControlModel).where(
                ModelAccessControlModel.model_id == model_id
            )
        )
        access_ctrl = result.scalar_one_or_none()

        if access_ctrl is None:
            access_ctrl = ModelAccessControlModel(
                model_id=model_id,
                allowed_roles=allowed_roles,
                max_tokens_per_request=max_tokens_per_request,
                enabled=enabled,
                rate_limit_per_minute=rate_limit_per_minute,
            )
            self.db.add(access_ctrl)
        else:
            access_ctrl.allowed_roles = allowed_roles
            access_ctrl.max_tokens_per_request = max_tokens_per_request
            access_ctrl.enabled = enabled
            access_ctrl.rate_limit_per_minute = rate_limit_per_minute

        await self.db.commit()

        return {
            "model_id": model_id,
            "allowed_roles": allowed_roles,
            "max_tokens_per_request": max_tokens_per_request,
            "enabled": enabled,
            "rate_limit_per_minute": rate_limit_per_minute,
        }

    async def get_model_access_config(self, model_id: str) -> Optional[dict]:
        result = await self.db.execute(
            select(ModelAccessControlModel).where(
                ModelAccessControlModel.model_id == model_id
            )
        )
        access_ctrl = result.scalar_one_or_none()
        if access_ctrl is None:
            return None

        return {
            "model_id": access_ctrl.model_id,
            "allowed_roles": access_ctrl.allowed_roles or [],
            "max_tokens_per_request": access_ctrl.max_tokens_per_request,
            "enabled": access_ctrl.enabled,
            "rate_limit_per_minute": access_ctrl.rate_limit_per_minute,
        }

    async def list_model_access_configs(self) -> list[dict]:
        result = await self.db.execute(select(ModelAccessControlModel))
        configs = result.scalars().all()
        return [
            {
                "model_id": c.model_id,
                "allowed_roles": c.allowed_roles or [],
                "max_tokens_per_request": c.max_tokens_per_request,
                "enabled": c.enabled,
                "rate_limit_per_minute": c.rate_limit_per_minute,
            }
            for c in configs
        ]

    async def delete_model_access(self, model_id: str) -> dict:
        from ..core.redis_client import cache_delete

        result = await self.db.execute(
            select(ModelAccessControlModel).where(
                ModelAccessControlModel.model_id == model_id
            )
        )
        access_ctrl = result.scalar_one_or_none()
        if access_ctrl is None:
            raise ValueError(f"No access control found for model '{model_id}'")

        await self.db.delete(access_ctrl)
        await self.db.commit()
        await cache_delete(f"model:access:{model_id}")

        return {"deleted": True, "message": f"Access control for '{model_id}' deleted"}
