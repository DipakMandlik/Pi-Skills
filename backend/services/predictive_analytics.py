"""
Predictive Cost Analytics - ML-based forecasting and cost projections
Uses time series analysis for trend prediction
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import TokenUsageLogModel, UserTokenModel, CostTrackingModel

logger = logging.getLogger("backend.predictive_analytics")


class PredictiveAnalytics:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def forecast_monthly_cost(
        self,
        user_id: str,
        months_ahead: int = 3,
    ) -> dict:
        now = datetime.now(timezone.utc)
        monthly_costs = []

        for i in range(6):
            month_date = now - timedelta(days=30 * (i + 1))
            period = month_date.strftime("%Y-%m")

            result = await self.db.execute(
                select(func.sum(CostTrackingModel.cost)).where(
                    CostTrackingModel.user_id == user_id,
                    CostTrackingModel.period == period,
                )
            )
            cost = result.scalar() or 0
            monthly_costs.append({"period": period, "cost": cost})

        monthly_costs.reverse()

        if len(monthly_costs) < 3:
            return {
                "forecast": [],
                "confidence": "low",
                "message": "Insufficient historical data",
            }

        costs = [m["cost"] for m in monthly_costs]
        avg_cost = sum(costs) / len(costs)
        trend = self._calculate_trend(costs)
        growth_rate = trend / avg_cost if avg_cost > 0 else 0

        forecast = []
        for i in range(1, months_ahead + 1):
            future_date = now + timedelta(days=30 * i)
            period = future_date.strftime("%Y-%m")
            projected_cost = avg_cost + (trend * i)
            projected_cost = max(0, projected_cost)

            forecast.append({
                "period": period,
                "projected_cost": round(projected_cost, 2),
                "lower_bound": round(projected_cost * 0.7, 2),
                "upper_bound": round(projected_cost * 1.3, 2),
            })

        return {
            "historical": monthly_costs,
            "forecast": forecast,
            "avg_monthly_cost": round(avg_cost, 2),
            "monthly_growth_rate": round(growth_rate * 100, 1),
            "confidence": "medium" if len(monthly_costs) >= 6 else "low",
        }

    async def project_token_runway(
        self,
        user_id: str,
        remaining_tokens: int,
    ) -> dict:
        now = datetime.now(timezone.utc)
        lookback_days = 30
        lookback = now - timedelta(days=lookback_days)

        result = await self.db.execute(
            select(
                func.sum(TokenUsageLogModel.tokens_used).label("total_tokens"),
                func.count(TokenUsageLogModel.id).label("total_requests"),
            ).where(
                TokenUsageLogModel.user_id == user_id,
                TokenUsageLogModel.timestamp >= lookback,
            )
        )
        row = result.one()
        total_tokens = row[0] or 0
        total_requests = row[1] or 0

        if total_tokens == 0:
            return {
                "runway_days": None,
                "daily_avg_tokens": 0,
                "daily_avg_requests": 0,
                "message": "No usage data available",
            }

        daily_avg_tokens = total_tokens / lookback_days
        daily_avg_requests = total_requests / lookback_days

        runway_days = remaining_tokens / daily_avg_tokens if daily_avg_tokens > 0 else None
        runway_date = now + timedelta(days=runway_days) if runway_days else None

        if runway_days and runway_days < 7:
            urgency = "critical"
        elif runway_days and runway_days < 14:
            urgency = "warning"
        else:
            urgency = "healthy"

        return {
            "runway_days": round(runway_days, 1) if runway_days else None,
            "runway_date": runway_date.strftime("%Y-%m-%d") if runway_date else None,
            "daily_avg_tokens": round(daily_avg_tokens),
            "daily_avg_requests": round(daily_avg_requests, 1),
            "remaining_tokens": remaining_tokens,
            "urgency": urgency,
            "suggestion": self._get_runway_suggestion(urgency, runway_days),
        }

    async def analyze_model_efficiency(
        self,
        user_id: Optional[str] = None,
        period: Optional[str] = None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        if period is None:
            period = now.strftime("%Y-%m")

        query = select(
            TokenUsageLogModel.model_id,
            func.sum(TokenUsageLogModel.tokens_used).label("total_tokens"),
            func.sum(TokenUsageLogModel.cost).label("total_cost"),
            func.count(TokenUsageLogModel.id).label("total_requests"),
            func.avg(TokenUsageLogModel.latency_ms).label("avg_latency"),
        ).where(
            TokenUsageLogModel.timestamp >= now - timedelta(days=30),
        ).group_by(TokenUsageLogModel.model_id)

        if user_id:
            query = query.where(TokenUsageLogModel.user_id == user_id)

        result = await self.db.execute(query)
        rows = result.all()

        models = []
        for row in rows:
            model_id, total_tokens, total_cost, total_requests, avg_latency = row
            if total_requests and total_requests > 0:
                cost_per_request = total_cost / total_requests if total_requests else 0
                tokens_per_request = total_tokens / total_requests if total_requests else 0
                efficiency_score = self._calculate_efficiency(
                    cost_per_request, tokens_per_request, avg_latency or 0
                )

                models.append({
                    "model_id": model_id,
                    "total_tokens": total_tokens or 0,
                    "total_cost": round(total_cost or 0, 4),
                    "total_requests": total_requests,
                    "avg_latency_ms": round(avg_latency or 0),
                    "cost_per_request": round(cost_per_request, 6),
                    "tokens_per_request": round(tokens_per_request),
                    "efficiency_score": round(efficiency_score, 2),
                })

        models.sort(key=lambda m: m["efficiency_score"], reverse=True)

        return {
            "models": models,
            "most_efficient": models[0] if models else None,
            "least_efficient": models[-1] if models else None,
            "period": period,
        }

    async def get_usage_recommendations(
        self,
        user_id: str,
    ) -> list[dict]:
        recommendations = []

        runway = await self.project_token_runway(user_id, 100000)
        if runway["urgency"] in ["critical", "warning"]:
            recommendations.append({
                "type": "TOKEN_CONSERVATION",
                "priority": "high",
                "title": "Token budget running low",
                "description": f"Estimated {runway['runway_days']} days remaining at current usage",
                "actions": [
                    "Consider using a cheaper model for simple tasks",
                    "Optimize prompts to reduce token usage",
                    "Review usage patterns for wasteful requests",
                ],
            })

        efficiency = await self.analyze_model_efficiency(user_id)
        if len(efficiency["models"]) > 1:
            most_eff = efficiency["most_efficient"]
            least_eff = efficiency["least_efficient"]
            if most_eff and least_eff and most_eff["efficiency_score"] > least_eff["efficiency_score"] * 2:
                recommendations.append({
                    "type": "MODEL_SWITCH",
                    "priority": "medium",
                    "title": f"Consider using {most_eff['model_id']} more",
                    "description": f"{most_eff['model_id']} is {most_eff['efficiency_score']/least_eff['efficiency_score']:.1f}x more efficient than {least_eff['model_id']}",
                    "actions": [
                        f"Route simple tasks to {most_eff['model_id']}",
                        f"Reserve {least_eff['model_id']} for complex tasks only",
                    ],
                })

        forecast = await self.forecast_monthly_cost(user_id)
        if forecast["monthly_growth_rate"] > 20:
            recommendations.append({
                "type": "COST_GROWTH",
                "priority": "high",
                "title": "Cost growth rate is high",
                "description": f"Monthly costs growing at {forecast['monthly_growth_rate']:.1f}%",
                "actions": [
                    "Review recent usage spikes",
                    "Consider upgrading to a higher tier plan",
                    "Implement stricter rate limits",
                ],
            })

        return recommendations

    def _calculate_trend(self, values: list[float]) -> float:
        n = len(values)
        if n < 2:
            return 0

        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0

        return numerator / denominator

    def _calculate_efficiency(
        self,
        cost_per_request: float,
        tokens_per_request: float,
        avg_latency: float,
    ) -> float:
        cost_score = 1 / (cost_per_request + 0.0001)
        latency_score = 1 / (avg_latency + 1)

        return (cost_score * 0.6 + latency_score * 0.4) * 100

    def _get_runway_suggestion(
        self,
        urgency: str,
        runway_days: Optional[float],
    ) -> str:
        if urgency == "critical":
            return "Immediate action required. Consider upgrading your plan or reducing usage."
        elif urgency == "warning":
            return "Token budget getting low. Review usage patterns and consider optimization."
        return "Token budget is healthy. Current usage is sustainable."
