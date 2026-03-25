"""
Auto-Scaling Recommendation Engine - Smart plan upgrade/downgrade suggestions
Uses usage pattern analysis to recommend optimal plans
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import TokenUsageLogModel, UserTokenModel
from ..services.subscription_service import SubscriptionService
from ..services.token_service import TokenService

logger = logging.getLogger("backend.auto_scaling")


class AutoScalingEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_svc = SubscriptionService(db)
        self.token_svc = TokenService(db)

    async def analyze_user_for_scaling(
        self,
        user_id: str,
    ) -> dict:
        plan = await self.subscription_svc.get_user_plan(user_id)
        if not plan:
            return {
                "recommendation": "assign_plan",
                "reason": "No active subscription",
                "suggested_plan": "free",
            }

        usage = await self.token_svc.get_user_token_usage(user_id)
        if not usage:
            return {
                "recommendation": "no_action",
                "reason": "No usage data available",
            }

        usage_pct = (usage["tokens_used"] / usage["tokens_limit"] * 100) if usage["tokens_limit"] > 0 else 0

        daily_usage = await self._get_daily_usage_pattern(user_id)
        projected_monthly = self._project_monthly_usage(daily_usage)

        all_plans = await self.subscription_svc.list_subscriptions()

        if usage_pct >= 95:
            return {
                "recommendation": "upgrade_urgent",
                "reason": f"Usage at {usage_pct:.1f}% - near limit",
                "current_plan": plan["plan_name"],
                "current_usage_pct": round(usage_pct, 1),
                "projected_monthly": projected_monthly,
                "suggested_plan": self._find_upgrade_plan(plan, all_plans, projected_monthly),
                "urgency": "critical",
            }
        elif usage_pct >= 80:
            return {
                "recommendation": "upgrade_suggested",
                "reason": f"Usage at {usage_pct:.1f}% - approaching limit",
                "current_plan": plan["plan_name"],
                "current_usage_pct": round(usage_pct, 1),
                "projected_monthly": projected_monthly,
                "suggested_plan": self._find_upgrade_plan(plan, all_plans, projected_monthly),
                "urgency": "warning",
            }
        elif usage_pct < 20 and plan["plan_name"] != "free":
            days_remaining = self._calculate_days_remaining(usage_pct)
            if days_remaining > 20:
                cheaper_plan = self._find_downgrade_plan(plan, all_plans, projected_monthly)
                if cheaper_plan:
                    return {
                        "recommendation": "downgrade_suggested",
                        "reason": f"Usage at {usage_pct:.1f}% - plan may be oversized",
                        "current_plan": plan["plan_name"],
                        "current_usage_pct": round(usage_pct, 1),
                        "projected_monthly": projected_monthly,
                        "suggested_plan": cheaper_plan,
                        "potential_savings": self._calculate_savings(plan, cheaper_plan, all_plans),
                        "urgency": "info",
                    }

        return {
            "recommendation": "no_action",
            "reason": f"Usage at {usage_pct:.1f}% - within optimal range",
            "current_plan": plan["plan_name"],
            "current_usage_pct": round(usage_pct, 1),
            "projected_monthly": projected_monthly,
            "urgency": "healthy",
        }

    async def get_all_scaling_recommendations(self) -> list[dict]:
        subs = await self.subscription_svc.list_user_subscriptions()
        recommendations = []

        for sub in subs:
            rec = await self.analyze_user_for_scaling(sub["user_id"])
            if rec["recommendation"] != "no_action":
                rec["user_id"] = sub["user_id"]
                recommendations.append(rec)

        recommendations.sort(key=lambda x: {
            "critical": 0,
            "warning": 1,
            "info": 2,
        }.get(x.get("urgency", "info"), 3))

        return recommendations

    async def get_plan_utilization_report(self) -> dict:
        plans = await self.subscription_svc.list_subscriptions()
        report = []

        for plan in plans:
            usage_stats = await self._get_plan_usage_stats(plan["plan_name"])
            report.append({
                "plan_name": plan["plan_name"],
                "display_name": plan["display_name"],
                "monthly_limit": plan["monthly_token_limit"],
                "total_users": usage_stats["total_users"],
                "avg_usage_pct": usage_stats["avg_usage_pct"],
                "max_usage_pct": usage_stats["max_usage_pct"],
                "users_near_limit": usage_stats["users_near_limit"],
                "utilization_status": self._get_utilization_status(usage_stats["avg_usage_pct"]),
            })

        return {
            "plans": report,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _get_daily_usage_pattern(self, user_id: str) -> list[dict]:
        now = datetime.now(timezone.utc)
        daily = []

        for i in range(14):
            day_start = (now - timedelta(days=i+1)).replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)

            result = await self.db.execute(
                select(
                    func.sum(TokenUsageLogModel.tokens_used).label("tokens"),
                    func.count(TokenUsageLogModel.id).label("requests"),
                ).where(
                    TokenUsageLogModel.user_id == user_id,
                    TokenUsageLogModel.timestamp >= day_start,
                    TokenUsageLogModel.timestamp < day_end,
                )
            )
            row = result.one()
            daily.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "tokens": row[0] or 0,
                "requests": row[1] or 0,
            })

        return list(reversed(daily))

    def _project_monthly_usage(self, daily_usage: list[dict]) -> int:
        if not daily_usage:
            return 0

        recent_7 = daily_usage[-7:] if len(daily_usage) >= 7 else daily_usage
        avg_daily = sum(d["tokens"] for d in recent_7) / len(recent_7)
        return int(avg_daily * 30)

    def _find_upgrade_plan(
        self,
        current_plan: dict,
        all_plans: list[dict],
        projected_usage: int,
    ) -> Optional[dict]:
        current_limit = current_plan["monthly_token_limit"]
        candidates = [
            p for p in all_plans
            if p["monthly_token_limit"] > current_limit
            and p["monthly_token_limit"] >= projected_usage
        ]

        if candidates:
            candidates.sort(key=lambda x: x["monthly_token_limit"])
            best = candidates[0]
            return {
                "plan_name": best["plan_name"],
                "display_name": best["display_name"],
                "monthly_limit": best["monthly_token_limit"],
            }

        if candidates or all_plans:
            upgrade = [p for p in all_plans if p["monthly_token_limit"] > current_limit]
            if upgrade:
                upgrade.sort(key=lambda x: x["monthly_token_limit"])
                best = upgrade[0]
                return {
                    "plan_name": best["plan_name"],
                    "display_name": best["display_name"],
                    "monthly_limit": best["monthly_token_limit"],
                }

        return None

    def _find_downgrade_plan(
        self,
        current_plan: dict,
        all_plans: list[dict],
        projected_usage: int,
    ) -> Optional[dict]:
        current_limit = current_plan["monthly_token_limit"]
        candidates = [
            p for p in all_plans
            if p["monthly_token_limit"] < current_limit
            and p["monthly_token_limit"] >= projected_usage * 1.5
        ]

        if candidates:
            candidates.sort(key=lambda x: x["monthly_token_limit"], reverse=True)
            best = candidates[0]
            return {
                "plan_name": best["plan_name"],
                "display_name": best["display_name"],
                "monthly_limit": best["monthly_token_limit"],
            }

        return None

    def _calculate_savings(
        self,
        current: dict,
        suggested: dict,
        all_plans: list[dict],
    ) -> Optional[float]:
        current_cost = next(
            (p["cost_budget_monthly"] for p in all_plans if p["plan_name"] == current["plan_name"]),
            0,
        )
        suggested_cost = next(
            (p["cost_budget_monthly"] for p in all_plans if p["plan_name"] == suggested["plan_name"]),
            0,
        )
        return round(current_cost - suggested_cost, 2)

    def _calculate_days_remaining(self, usage_pct: float) -> int:
        now = datetime.now(timezone.utc)
        days_in_month = 30
        days_elapsed = now.day
        if usage_pct > 0:
            daily_rate = usage_pct / days_elapsed
            remaining_pct = 100 - usage_pct
            return int(remaining_pct / daily_rate) if daily_rate > 0 else 30
        return 30

    async def _get_plan_usage_stats(self, plan_name: str) -> dict:
        return {
            "total_users": 0,
            "avg_usage_pct": 0.0,
            "max_usage_pct": 0.0,
            "users_near_limit": 0,
        }

    def _get_utilization_status(self, avg_pct: float) -> str:
        if avg_pct >= 80:
            return "high"
        elif avg_pct >= 50:
            return "moderate"
        elif avg_pct >= 20:
            return "low"
        else:
            return "underutilized"
