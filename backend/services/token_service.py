"""
Token Service - Manages token estimation, validation, and consumption tracking
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import UserTokenModel, TokenUsageLogModel, CostTrackingModel, RegisteredModelModel
from ..core.redis_client import cache_get, cache_set, cache_incr, cache_delete

logger = logging.getLogger("backend.token_service")

_CACHE_TTL = 60


class TokenService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def calculate_cost(self, tokens: int, cost_per_1k: float) -> float:
        return (tokens / 1000) * cost_per_1k

    async def get_model_cost_per_1k(self, model_id: str) -> float:
        cache_key = f"model:cost:{model_id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached.get("cost_per_1k", 0.0)

        result = await self.db.execute(
            select(RegisteredModelModel).where(
                RegisteredModelModel.model_id == model_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return 0.0

        cost = model.cost_per_1k_tokens if model.cost_per_1k_tokens else 0.0
        await cache_set(cache_key, {"cost_per_1k": cost}, 300)
        return cost

    async def get_current_period(self) -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m")

    async def get_user_token_usage(self, user_id: str) -> Optional[dict]:
        period = await self.get_current_period()
        cache_key = f"tokens:{user_id}:{period}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        result = await self.db.execute(
            select(UserTokenModel).where(
                UserTokenModel.user_id == user_id,
                UserTokenModel.period == period,
            )
        )
        token_model = result.scalar_one_or_none()
        if token_model is None:
            return None

        usage = {
            "user_id": user_id,
            "period": period,
            "tokens_used": token_model.tokens_used,
            "tokens_limit": token_model.tokens_limit,
            "cost_accumulated": token_model.cost_accumulated,
            "remaining_tokens": max(0, token_model.tokens_limit - token_model.tokens_used),
        }

        await cache_set(cache_key, usage, _CACHE_TTL)
        return usage

    async def validate_tokens_available(
        self, user_id: str, estimated_tokens: int, monthly_limit: int
    ) -> dict:
        usage = await self.get_user_token_usage(user_id)
        period = await self.get_current_period()

        if usage is None:
            usage = {
                "user_id": user_id,
                "period": period,
                "tokens_used": 0,
                "tokens_limit": monthly_limit,
                "cost_accumulated": 0.0,
                "remaining_tokens": monthly_limit,
            }

        remaining = usage["remaining_tokens"]
        if estimated_tokens > remaining:
            return {
                "allowed": False,
                "reason": "TOKEN_BUDGET_EXCEEDED",
                "message": f"Insufficient tokens. Remaining: {remaining}, Requested: {estimated_tokens}",
                "tokens_used": usage["tokens_used"],
                "tokens_limit": usage["tokens_limit"],
                "remaining_tokens": remaining,
            }

        return {
            "allowed": True,
            "tokens_used": usage["tokens_used"],
            "tokens_limit": usage["tokens_limit"],
            "remaining_tokens": remaining,
        }

    async def deduct_tokens(
        self,
        user_id: str,
        model_id: str,
        tokens_used: int,
        cost: float,
        request_id: Optional[str] = None,
        skill_id: Optional[str] = None,
        latency_ms: Optional[int] = None,
        outcome: str = "SUCCESS",
    ) -> dict:
        period = await self.get_current_period()

        result = await self.db.execute(
            select(UserTokenModel).where(
                UserTokenModel.user_id == user_id,
                UserTokenModel.period == period,
            )
        )
        token_model = result.scalar_one_or_none()

        if token_model is None:
            token_model = UserTokenModel(
                id=str(uuid4()),
                user_id=user_id,
                period=period,
                tokens_used=0,
                tokens_limit=0,
                cost_accumulated=0.0,
            )
            self.db.add(token_model)

        token_model.tokens_used += tokens_used
        token_model.cost_accumulated += cost

        log_entry = TokenUsageLogModel(
            id=str(uuid4()),
            user_id=user_id,
            model_id=model_id,
            skill_id=skill_id,
            tokens_used=tokens_used,
            cost=cost,
            request_id=request_id,
            latency_ms=latency_ms,
            outcome=outcome,
        )
        self.db.add(log_entry)

        cost_entry = CostTrackingModel(
            id=str(uuid4()),
            user_id=user_id,
            period=period,
            model_id=model_id,
            tokens_used=tokens_used,
            cost=cost,
        )
        self.db.add(cost_entry)

        await self.db.commit()

        await cache_delete(f"tokens:{user_id}:{period}")

        return {
            "user_id": user_id,
            "tokens_used_total": token_model.tokens_used,
            "tokens_limit": token_model.tokens_limit,
            "cost_accumulated": token_model.cost_accumulated,
            "remaining_tokens": max(0, token_model.tokens_limit - token_model.tokens_used),
        }

    async def initialize_user_tokens(
        self, user_id: str, monthly_limit: int
    ) -> dict:
        period = await self.get_current_period()

        existing = await self.db.execute(
            select(UserTokenModel).where(
                UserTokenModel.user_id == user_id,
                UserTokenModel.period == period,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return {"status": "already_initialized", "period": period}

        token_model = UserTokenModel(
            id=str(uuid4()),
            user_id=user_id,
            period=period,
            tokens_used=0,
            tokens_limit=monthly_limit,
            cost_accumulated=0.0,
        )
        self.db.add(token_model)
        await self.db.commit()

        await cache_delete(f"tokens:{user_id}:{period}")

        return {
            "status": "initialized",
            "user_id": user_id,
            "period": period,
            "tokens_limit": monthly_limit,
        }

    async def get_token_usage_stats(
        self, user_id: str, period: Optional[str] = None
    ) -> dict:
        if period is None:
            period = await self.get_current_period()

        result = await self.db.execute(
            select(
                TokenUsageLogModel.model_id,
                func.sum(TokenUsageLogModel.tokens_used).label("total_tokens"),
                func.sum(TokenUsageLogModel.cost).label("total_cost"),
                func.count(TokenUsageLogModel.id).label("request_count"),
            )
            .where(
                TokenUsageLogModel.user_id == user_id,
                func.strftime("%Y-%m", TokenUsageLogModel.timestamp) == period,
            )
            .group_by(TokenUsageLogModel.model_id)
        )

        model_stats = []
        for row in result.all():
            model_stats.append({
                "model_id": row[0],
                "total_tokens": row[1] or 0,
                "total_cost": row[2] or 0.0,
                "request_count": row[3] or 0,
            })

        usage = await self.get_user_token_usage(user_id)

        return {
            "user_id": user_id,
            "period": period,
            "usage": usage,
            "model_breakdown": model_stats,
        }

    async def check_budget_alert(
        self, user_id: str, cost_budget: float
    ) -> dict:
        period = await self.get_current_period()
        usage = await self.get_user_token_usage(user_id)

        if usage is None:
            return {
                "alert": False,
                "level": "none",
                "cost_used": 0.0,
                "cost_budget": cost_budget,
                "percentage": 0.0,
            }

        cost_used = usage.get("cost_accumulated", 0.0)
        percentage = (cost_used / cost_budget * 100) if cost_budget > 0 else 0

        level = "none"
        if percentage >= 100:
            level = "critical"
        elif percentage >= 90:
            level = "warning"
        elif percentage >= 75:
            level = "caution"

        return {
            "alert": level != "none",
            "level": level,
            "cost_used": cost_used,
            "cost_budget": cost_budget,
            "percentage": round(percentage, 2),
            "period": period,
        }

    async def get_usage_trend(
        self, user_id: str, months: int = 6
    ) -> list[dict]:
        now = datetime.now(timezone.utc)
        periods = []
        for i in range(months):
            month = now.month - i
            year = now.year
            while month <= 0:
                month += 12
                year -= 1
            periods.append(f"{year:04d}-{month:02d}")

        result = await self.db.execute(
            select(UserTokenModel).where(
                UserTokenModel.user_id == user_id,
                UserTokenModel.period.in_(periods),
            ).order_by(UserTokenModel.period)
        )

        usage_by_period = {}
        for ut in result.scalars().all():
            usage_by_period[ut.period] = {
                "period": ut.period,
                "tokens_used": ut.tokens_used,
                "tokens_limit": ut.tokens_limit,
                "cost_accumulated": ut.cost_accumulated,
            }

        trend = []
        for p in periods:
            if p in usage_by_period:
                trend.append(usage_by_period[p])
            else:
                trend.append({
                    "period": p,
                    "tokens_used": 0,
                    "tokens_limit": 0,
                    "cost_accumulated": 0.0,
                })

        return trend

    async def get_global_usage_stats(
        self, period: Optional[str] = None
    ) -> dict:
        if period is None:
            period = await self.get_current_period()

        result = await self.db.execute(
            select(
                func.sum(TokenUsageLogModel.tokens_used).label("total_tokens"),
                func.sum(TokenUsageLogModel.cost).label("total_cost"),
                func.count(TokenUsageLogModel.id).label("total_requests"),
                func.count(func.distinct(TokenUsageLogModel.user_id)).label("unique_users"),
            ).where(
                func.strftime("%Y-%m", TokenUsageLogModel.timestamp) == period,
            )
        )
        row = result.one()

        model_result = await self.db.execute(
            select(
                TokenUsageLogModel.model_id,
                func.sum(TokenUsageLogModel.tokens_used).label("tokens"),
                func.sum(TokenUsageLogModel.cost).label("cost"),
                func.count(TokenUsageLogModel.id).label("requests"),
            )
            .where(
                func.strftime("%Y-%m", TokenUsageLogModel.timestamp) == period,
            )
            .group_by(TokenUsageLogModel.model_id)
            .order_by(func.sum(TokenUsageLogModel.tokens_used).desc())
        )

        model_breakdown = []
        for mrow in model_result.all():
            model_breakdown.append({
                "model_id": mrow[0],
                "total_tokens": mrow[1] or 0,
                "total_cost": mrow[2] or 0.0,
                "request_count": mrow[3] or 0,
            })

        return {
            "period": period,
            "total_tokens": row[0] or 0,
            "total_cost": row[1] or 0.0,
            "total_requests": row[2] or 0,
            "unique_users": row[3] or 0,
            "model_breakdown": model_breakdown,
        }

    async def reset_user_tokens(
        self, user_id: str, new_limit: int
    ) -> dict:
        period = await self.get_current_period()

        result = await self.db.execute(
            select(UserTokenModel).where(
                UserTokenModel.user_id == user_id,
                UserTokenModel.period == period,
            )
        )
        token_model = result.scalar_one_or_none()

        if token_model is None:
            return await self.initialize_user_tokens(user_id, new_limit)

        token_model.tokens_used = 0
        token_model.tokens_limit = new_limit
        token_model.cost_accumulated = 0.0
        token_model.last_reset = datetime.now(timezone.utc)

        await self.db.commit()
        await cache_delete(f"tokens:{user_id}:{period}")

        return {
            "status": "reset",
            "user_id": user_id,
            "period": period,
            "new_limit": new_limit,
        }

    async def get_usage_logs(
        self,
        user_id: Optional[str] = None,
        model_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        query = select(TokenUsageLogModel).order_by(
            TokenUsageLogModel.timestamp.desc()
        )

        if user_id:
            query = query.where(TokenUsageLogModel.user_id == user_id)
        if model_id:
            query = query.where(TokenUsageLogModel.model_id == model_id)

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        logs = result.scalars().all()

        return {
            "logs": [
                {
                    "id": str(log.id),
                    "user_id": str(log.user_id),
                    "model_id": log.model_id,
                    "skill_id": log.skill_id,
                    "tokens_used": log.tokens_used,
                    "cost": log.cost,
                    "request_id": str(log.request_id) if log.request_id else None,
                    "latency_ms": log.latency_ms,
                    "outcome": log.outcome,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                }
                for log in logs
            ],
            "total": len(logs),
            "offset": offset,
            "limit": limit,
        }
