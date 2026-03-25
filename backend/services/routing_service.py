"""
Routing Service - Selects appropriate model based on task type and constraints
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import RegisteredModelModel, FeatureFlagModel
from ..core.redis_client import cache_get, cache_set

logger = logging.getLogger("backend.routing_service")

_CACHE_TTL = 300


class RoutingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def select_model(
        self,
        user_id: str,
        task_type: str,
        requested_model: Optional[str] = None,
        allowed_models: Optional[list[str]] = None,
        token_budget: Optional[int] = None,
    ) -> dict:
        if requested_model:
            return await self._validate_requested_model(
                requested_model, allowed_models, token_budget
            )

        return await self._auto_select_model(
            user_id, task_type, allowed_models, token_budget
        )

    async def _validate_requested_model(
        self,
        model_id: str,
        allowed_models: Optional[list[str]],
        token_budget: Optional[int],
    ) -> dict:
        result = await self.db.execute(
            select(RegisteredModelModel).where(
                RegisteredModelModel.model_id == model_id,
                RegisteredModelModel.is_available == True,
            )
        )
        model = result.scalar_one_or_none()

        if model is None:
            return {
                "selected": False,
                "reason": "MODEL_NOT_AVAILABLE",
                "message": f"Model '{model_id}' is not available",
            }

        if allowed_models and model_id not in allowed_models:
            return {
                "selected": False,
                "reason": "MODEL_NOT_ALLOWED",
                "message": f"Model '{model_id}' not in allowed models",
            }

        if token_budget and model.max_tokens and token_budget > model.max_tokens:
            return {
                "selected": False,
                "reason": "TOKEN_BUDGET_EXCEEDED",
                "message": f"Token budget ({token_budget}) exceeds model limit ({model.max_tokens})",
            }

        return {
            "selected": True,
            "model_id": model.model_id,
            "display_name": model.display_name,
            "provider": model.provider,
            "tier": model.tier,
            "max_tokens": model.max_tokens,
        }

    async def _auto_select_model(
        self,
        user_id: str,
        task_type: str,
        allowed_models: Optional[list[str]],
        token_budget: Optional[int],
    ) -> dict:
        query = select(RegisteredModelModel).where(
            RegisteredModelModel.is_available == True
        )

        if allowed_models:
            query = query.where(RegisteredModelModel.model_id.in_(allowed_models))

        query = query.order_by(RegisteredModelModel.tier.desc())

        result = await self.db.execute(query)
        models = result.scalars().all()

        if not models:
            return {
                "selected": False,
                "reason": "NO_MODELS_AVAILABLE",
                "message": "No models available for selection",
            }

        for model in models:
            if token_budget and model.max_tokens and token_budget > model.max_tokens:
                continue

            feature_result = await self.db.execute(
                select(FeatureFlagModel).where(
                    FeatureFlagModel.model_id == model.model_id,
                    FeatureFlagModel.feature_name == task_type,
                    FeatureFlagModel.enabled == True,
                )
            )
            feature = feature_result.scalar_one_or_none()
            if feature is not None:
                return {
                    "selected": True,
                    "model_id": model.model_id,
                    "display_name": model.display_name,
                    "provider": model.provider,
                    "tier": model.tier,
                    "max_tokens": model.max_tokens,
                    "selection_reason": "FEATURE_MATCH",
                }

        fallback = models[0]
        return {
            "selected": True,
            "model_id": fallback.model_id,
            "display_name": fallback.display_name,
            "provider": fallback.provider,
            "tier": fallback.tier,
            "max_tokens": fallback.max_tokens,
            "selection_reason": "FALLBACK",
        }

    async def get_available_models(
        self, allowed_models: Optional[list[str]] = None
    ) -> list[dict]:
        query = select(RegisteredModelModel).where(
            RegisteredModelModel.is_available == True
        )

        if allowed_models:
            query = query.where(RegisteredModelModel.model_id.in_(allowed_models))

        result = await self.db.execute(query)
        models = result.scalars().all()

        return [
            {
                "model_id": m.model_id,
                "display_name": m.display_name,
                "provider": m.provider,
                "tier": m.tier,
                "max_tokens": m.max_tokens,
            }
            for m in models
        ]

    async def get_feature_flags(self, model_id: Optional[str] = None) -> list[dict]:
        query = select(FeatureFlagModel)
        if model_id:
            query = query.where(FeatureFlagModel.model_id == model_id)

        result = await self.db.execute(query)
        flags = result.scalars().all()

        return [
            {
                "feature_name": f.feature_name,
                "model_id": f.model_id,
                "enabled_for": f.enabled_for or [],
                "enabled": f.enabled,
                "config": f.config or {},
            }
            for f in flags
        ]

    async def set_feature_flag(
        self,
        feature_name: str,
        model_id: str,
        enabled: bool = True,
        enabled_for: Optional[list[str]] = None,
        config: Optional[dict] = None,
    ) -> dict:
        result = await self.db.execute(
            select(FeatureFlagModel).where(
                FeatureFlagModel.feature_name == feature_name,
                FeatureFlagModel.model_id == model_id,
            )
        )
        flag = result.scalar_one_or_none()

        if flag is None:
            flag = FeatureFlagModel(
                feature_name=feature_name,
                model_id=model_id,
                enabled=enabled,
                enabled_for=enabled_for or [],
                config=config or {},
            )
            self.db.add(flag)
        else:
            flag.enabled = enabled
            flag.enabled_for = enabled_for or []
            flag.config = config or {}

        await self.db.commit()

        return {
            "feature_name": feature_name,
            "model_id": model_id,
            "enabled": enabled,
            "enabled_for": enabled_for or [],
            "config": config or {},
        }

    async def delete_feature_flag(self, feature_name: str, model_id: str) -> dict:
        result = await self.db.execute(
            select(FeatureFlagModel).where(
                FeatureFlagModel.feature_name == feature_name,
                FeatureFlagModel.model_id == model_id,
            )
        )
        flag = result.scalar_one_or_none()
        if flag is None:
            raise ValueError(f"Feature flag '{feature_name}' for model '{model_id}' not found")

        await self.db.delete(flag)
        await self.db.commit()

        return {"deleted": True, "message": f"Feature flag '{feature_name}' deleted"}
