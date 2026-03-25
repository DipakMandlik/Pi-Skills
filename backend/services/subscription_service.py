"""
Subscription Service - Manages user subscription plans and limits
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import SubscriptionModel, UserSubscriptionModel
from ..core.redis_client import cache_get, cache_delete, cache_set

logger = logging.getLogger("backend.subscription_service")

_CACHE_TTL = 300


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_plan(self, user_id: str) -> Optional[dict]:
        cache_key = f"subscription:{user_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        result = await self.db.execute(
            select(UserSubscriptionModel).where(
                UserSubscriptionModel.user_id == user_id,
                UserSubscriptionModel.is_active == True,
            )
        )
        user_sub = result.scalar_one_or_none()
        if user_sub is None:
            return None

        plan_result = await self.db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.plan_name == user_sub.plan_name,
                SubscriptionModel.is_active == True,
            )
        )
        plan = plan_result.scalar_one_or_none()
        if plan is None:
            return None

        plan_data = {
            "plan_name": plan.plan_name,
            "display_name": plan.display_name,
            "monthly_token_limit": plan.monthly_token_limit,
            "max_tokens_per_request": plan.max_tokens_per_request,
            "allowed_models": plan.allowed_models or [],
            "features": plan.features or [],
            "priority": plan.priority,
            "rate_limit_per_minute": plan.rate_limit_per_minute,
            "cost_budget_monthly": plan.cost_budget_monthly,
        }

        await cache_set(cache_key, plan_data, _CACHE_TTL)
        return plan_data

    async def validate_token_limit(
        self, user_id: str, estimated_tokens: int
    ) -> dict:
        plan = await self.get_user_plan(user_id)
        if plan is None:
            return {
                "allowed": False,
                "reason": "NO_SUBSCRIPTION",
                "message": "No active subscription found",
            }

        if estimated_tokens > plan["max_tokens_per_request"]:
            return {
                "allowed": False,
                "reason": "TOKEN_LIMIT_EXCEEDED",
                "message": f"Request exceeds max tokens per request ({plan['max_tokens_per_request']})",
            }

        return {
            "allowed": True,
            "plan": plan,
            "remaining_tokens": plan["monthly_token_limit"],
        }

    async def validate_model_access(self, user_id: str, model_id: str) -> dict:
        plan = await self.get_user_plan(user_id)
        if plan is None:
            return {
                "allowed": False,
                "reason": "NO_SUBSCRIPTION",
                "message": "No active subscription found",
            }

        allowed_models = plan.get("allowed_models", [])
        if model_id not in allowed_models:
            return {
                "allowed": False,
                "reason": "MODEL_NOT_ALLOWED",
                "message": f"Model '{model_id}' not in subscription plan",
            }

        return {"allowed": True, "plan": plan}

    async def create_subscription(
        self,
        plan_name: str,
        display_name: str,
        monthly_token_limit: int,
        max_tokens_per_request: int = 4096,
        allowed_models: list[str] | None = None,
        features: list[str] | None = None,
        priority: str = "standard",
        rate_limit_per_minute: int = 60,
        cost_budget_monthly: float = 0.0,
    ) -> dict:
        existing = await self.db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.plan_name == plan_name
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Subscription plan '{plan_name}' already exists")

        plan = SubscriptionModel(
            plan_name=plan_name,
            display_name=display_name,
            monthly_token_limit=monthly_token_limit,
            max_tokens_per_request=max_tokens_per_request,
            allowed_models=allowed_models or [],
            features=features or [],
            priority=priority,
            rate_limit_per_minute=rate_limit_per_minute,
            cost_budget_monthly=cost_budget_monthly,
            is_active=True,
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)

        return {
            "plan_name": plan.plan_name,
            "display_name": plan.display_name,
            "monthly_token_limit": plan.monthly_token_limit,
            "max_tokens_per_request": plan.max_tokens_per_request,
            "allowed_models": plan.allowed_models,
            "features": plan.features,
            "priority": plan.priority,
            "rate_limit_per_minute": plan.rate_limit_per_minute,
            "cost_budget_monthly": plan.cost_budget_monthly,
        }

    async def assign_plan_to_user(
        self, user_id: str, plan_name: str, assigned_by: str
    ) -> dict:
        plan_check = await self.db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.plan_name == plan_name,
                SubscriptionModel.is_active == True,
            )
        )
        if plan_check.scalar_one_or_none() is None:
            raise ValueError(f"Plan '{plan_name}' not found or inactive")

        existing = await self.db.execute(
            select(UserSubscriptionModel).where(
                UserSubscriptionModel.user_id == user_id,
                UserSubscriptionModel.is_active == True,
            )
        )
        existing_sub = existing.scalar_one_or_none()
        if existing_sub is not None:
            existing_sub.is_active = False

        user_sub = UserSubscriptionModel(
            user_id=user_id,
            plan_name=plan_name,
            assigned_by=assigned_by,
            is_active=True,
        )
        self.db.add(user_sub)
        await self.db.commit()

        await cache_delete(f"subscription:{user_id}")

        return {
            "user_id": user_id,
            "plan_name": plan_name,
            "assigned_at": user_sub.assigned_at.isoformat() if user_sub.assigned_at else None,
        }

    async def list_subscriptions(self) -> list[dict]:
        result = await self.db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.is_active == True
            )
        )
        plans = result.scalars().all()
        return [
            {
                "plan_name": p.plan_name,
                "display_name": p.display_name,
                "monthly_token_limit": p.monthly_token_limit,
                "max_tokens_per_request": p.max_tokens_per_request,
                "allowed_models": p.allowed_models or [],
                "features": p.features or [],
                "priority": p.priority,
                "rate_limit_per_minute": p.rate_limit_per_minute,
                "cost_budget_monthly": p.cost_budget_monthly,
            }
            for p in plans
        ]

    async def get_user_plan_info(self, user_id: str) -> Optional[dict]:
        result = await self.db.execute(
            select(UserSubscriptionModel).where(
                UserSubscriptionModel.user_id == user_id,
                UserSubscriptionModel.is_active == True,
            )
        )
        user_sub = result.scalar_one_or_none()
        if user_sub is None:
            return None

        plan = await self.get_user_plan(user_id)
        return {
            "user_id": user_id,
            "plan_name": user_sub.plan_name,
            "assigned_at": user_sub.assigned_at.isoformat() if user_sub.assigned_at else None,
            "plan_details": plan,
        }

    async def update_subscription(
        self,
        plan_name: str,
        display_name: Optional[str] = None,
        monthly_token_limit: Optional[int] = None,
        max_tokens_per_request: Optional[int] = None,
        allowed_models: Optional[list[str]] = None,
        features: Optional[list[str]] = None,
        priority: Optional[str] = None,
        rate_limit_per_minute: Optional[int] = None,
        cost_budget_monthly: Optional[float] = None,
    ) -> dict:
        result = await self.db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.plan_name == plan_name,
                SubscriptionModel.is_active == True,
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise ValueError(f"Plan '{plan_name}' not found")

        if display_name is not None:
            plan.display_name = display_name
        if monthly_token_limit is not None:
            plan.monthly_token_limit = monthly_token_limit
        if max_tokens_per_request is not None:
            plan.max_tokens_per_request = max_tokens_per_request
        if allowed_models is not None:
            plan.allowed_models = allowed_models
        if features is not None:
            plan.features = features
        if priority is not None:
            plan.priority = priority
        if rate_limit_per_minute is not None:
            plan.rate_limit_per_minute = rate_limit_per_minute
        if cost_budget_monthly is not None:
            plan.cost_budget_monthly = cost_budget_monthly

        plan.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        return {
            "plan_name": plan.plan_name,
            "display_name": plan.display_name,
            "monthly_token_limit": plan.monthly_token_limit,
            "max_tokens_per_request": plan.max_tokens_per_request,
            "allowed_models": plan.allowed_models or [],
            "features": plan.features or [],
            "priority": plan.priority,
            "rate_limit_per_minute": plan.rate_limit_per_minute,
            "cost_budget_monthly": plan.cost_budget_monthly,
        }

    async def delete_subscription(self, plan_name: str) -> dict:
        result = await self.db.execute(
            select(SubscriptionModel).where(
                SubscriptionModel.plan_name == plan_name,
                SubscriptionModel.is_active == True,
            )
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise ValueError(f"Plan '{plan_name}' not found")

        plan.is_active = False
        plan.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        user_subs = await self.db.execute(
            select(UserSubscriptionModel).where(
                UserSubscriptionModel.plan_name == plan_name,
                UserSubscriptionModel.is_active == True,
            )
        )
        for user_sub in user_subs.scalars().all():
            user_sub.is_active = False
            await cache_delete(f"subscription:{user_sub.user_id}")

        await self.db.commit()
        return {"plan_name": plan_name, "deleted": True}

    async def list_user_subscriptions(self) -> list[dict]:
        result = await self.db.execute(
            select(UserSubscriptionModel).where(
                UserSubscriptionModel.is_active == True
            )
        )
        user_subs = result.scalars().all()
        return [
            {
                "user_id": str(us.user_id),
                "plan_name": us.plan_name,
                "assigned_at": us.assigned_at.isoformat() if us.assigned_at else None,
                "assigned_by": str(us.assigned_by) if us.assigned_by else None,
            }
            for us in user_subs
        ]
