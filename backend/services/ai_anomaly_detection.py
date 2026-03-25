"""
AI Anomaly Detection Engine - Detects unusual patterns in AI usage
Uses statistical analysis and ML-like pattern matching
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import TokenUsageLogModel, UserTokenModel, CostTrackingModel
from ..core.redis_client import cache_get, cache_set

logger = logging.getLogger("backend.ai_anomaly_detection")


class AnomalyDetectionEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_usage_anomalies(
        self,
        user_id: Optional[str] = None,
        lookback_hours: int = 24,
    ) -> dict:
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=lookback_hours)

        query = select(
            TokenUsageLogModel.user_id,
            TokenUsageLogModel.model_id,
            func.count(TokenUsageLogModel.id).label("request_count"),
            func.sum(TokenUsageLogModel.tokens_used).label("total_tokens"),
            func.sum(TokenUsageLogModel.cost).label("total_cost"),
            func.avg(TokenUsageLogModel.latency_ms).label("avg_latency"),
            func.max(TokenUsageLogModel.tokens_used).label("max_tokens"),
        ).where(
            TokenUsageLogModel.timestamp >= lookback,
        ).group_by(
            TokenUsageLogModel.user_id,
            TokenUsageLogModel.model_id,
        )

        if user_id:
            query = query.where(TokenUsageLogModel.user_id == user_id)

        result = await self.db.execute(query)
        rows = result.all()

        anomalies = []
        for row in rows:
            row_anomalies = await self._analyze_usage_row(row, lookback_hours)
            if row_anomalies:
                anomalies.extend(row_anomalies)

        return {
            "anomalies": anomalies,
            "total_anomalies": len(anomalies),
            "lookback_hours": lookback_hours,
            "analyzed_at": now.isoformat(),
        }

    async def _analyze_usage_row(self, row, lookback_hours: int) -> list[dict]:
        anomalies = []
        user_id, model_id, request_count, total_tokens, total_cost, avg_latency, max_tokens = row

        hourly_rate = request_count / lookback_hours if lookback_hours > 0 else 0

        if hourly_rate > 100:
            anomalies.append({
                "type": "HIGH_REQUEST_RATE",
                "severity": "critical",
                "user_id": str(user_id),
                "model_id": model_id,
                "metric": "requests_per_hour",
                "value": round(hourly_rate, 2),
                "threshold": 100,
                "message": f"Unusually high request rate: {hourly_rate:.1f} req/hr",
            })
        elif hourly_rate > 50:
            anomalies.append({
                "type": "ELEVATED_REQUEST_RATE",
                "severity": "warning",
                "user_id": str(user_id),
                "model_id": model_id,
                "metric": "requests_per_hour",
                "value": round(hourly_rate, 2),
                "threshold": 50,
                "message": f"Elevated request rate: {hourly_rate:.1f} req/hr",
            })

        if total_tokens and total_tokens > 1000000:
            anomalies.append({
                "type": "EXCESSIVE_TOKEN_USAGE",
                "severity": "critical",
                "user_id": str(user_id),
                "model_id": model_id,
                "metric": "total_tokens",
                "value": total_tokens,
                "threshold": 1000000,
                "message": f"Excessive token usage: {total_tokens:,} tokens in {lookback_hours}h",
            })

        if total_cost and total_cost > 100:
            anomalies.append({
                "type": "COST_SPIKE",
                "severity": "critical",
                "user_id": str(user_id),
                "model_id": model_id,
                "metric": "total_cost",
                "value": round(total_cost, 2),
                "threshold": 100,
                "message": f"Cost spike detected: ${total_cost:.2f} in {lookback_hours}h",
            })

        if avg_latency and avg_latency > 30000:
            anomalies.append({
                "type": "HIGH_LATENCY",
                "severity": "warning",
                "user_id": str(user_id),
                "model_id": model_id,
                "metric": "avg_latency_ms",
                "value": round(avg_latency),
                "threshold": 30000,
                "message": f"High average latency: {avg_latency/1000:.1f}s",
            })

        if max_tokens and max_tokens > 50000:
            anomalies.append({
                "type": "LARGE_SINGLE_REQUEST",
                "severity": "warning",
                "user_id": str(user_id),
                "model_id": model_id,
                "metric": "max_tokens",
                "value": max_tokens,
                "threshold": 50000,
                "message": f"Single request used {max_tokens:,} tokens",
            })

        return anomalies

    async def detect_cost_trend_anomalies(
        self,
        user_id: str,
        days: int = 30,
    ) -> dict:
        now = datetime.now(timezone.utc)
        daily_costs = []

        for day_offset in range(days):
            day_start = now - timedelta(days=day_offset + 1)
            day_end = now - timedelta(days=day_offset)

            result = await self.db.execute(
                select(func.sum(CostTrackingModel.cost)).where(
                    CostTrackingModel.user_id == user_id,
                    CostTrackingModel.recorded_at >= day_start,
                    CostTrackingModel.recorded_at < day_end,
                )
            )
            cost = result.scalar() or 0
            daily_costs.append(cost)

        if len(daily_costs) < 7:
            return {"trend": "insufficient_data", "anomalies": []}

        recent_avg = sum(daily_costs[:7]) / 7
        historical_avg = sum(daily_costs[7:]) / max(1, len(daily_costs) - 7)

        anomalies = []
        if historical_avg > 0 and recent_avg > historical_avg * 3:
            anomalies.append({
                "type": "COST_TREND_SPIKE",
                "severity": "critical",
                "metric": "daily_cost_ratio",
                "value": round(recent_avg / historical_avg, 2),
                "threshold": 3.0,
                "message": f"Cost trend spike: {recent_avg/historical_avg:.1f}x normal",
            })

        std_dev = self._calculate_std(daily_costs)
        mean_cost = sum(daily_costs) / len(daily_costs)
        for i, cost in enumerate(daily_costs[:7]):
            if std_dev > 0 and abs(cost - mean_cost) > 3 * std_dev:
                anomalies.append({
                    "type": "DAILY_COST_OUTLIER",
                    "severity": "warning",
                    "day_offset": i,
                    "value": round(cost, 2),
                    "mean": round(mean_cost, 2),
                    "std_dev": round(std_dev, 2),
                    "message": f"Day {i+1} cost outlier: ${cost:.2f} (mean: ${mean_cost:.2f})",
                })

        return {
            "trend": "spike" if recent_avg > historical_avg * 1.5 else "stable",
            "recent_daily_avg": round(recent_avg, 2),
            "historical_daily_avg": round(historical_avg, 2),
            "anomalies": anomalies,
        }

    async def detect_burst_patterns(
        self,
        user_id: Optional[str] = None,
        window_minutes: int = 5,
    ) -> dict:
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=1)

        query = select(TokenUsageLogModel).where(
            TokenUsageLogModel.timestamp >= lookback,
        ).order_by(TokenUsageLogModel.timestamp)

        if user_id:
            query = query.where(TokenUsageLogModel.user_id == user_id)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        user_timestamps: dict[str, list[datetime]] = defaultdict(list)
        for log in logs:
            user_timestamps[str(log.user_id)].append(log.timestamp)

        bursts = []
        for uid, timestamps in user_timestamps.items():
            timestamps.sort()
            for i in range(len(timestamps)):
                window_end = timestamps[i] + timedelta(minutes=window_minutes)
                count = sum(1 for t in timestamps[i:] if t <= window_end)

                if count > 20:
                    bursts.append({
                        "type": "REQUEST_BURST",
                        "severity": "critical" if count > 50 else "warning",
                        "user_id": uid,
                        "count": count,
                        "window_minutes": window_minutes,
                        "start_time": timestamps[i].isoformat(),
                        "message": f"Burst: {count} requests in {window_minutes} min",
                    })
                    break

        return {
            "bursts": bursts,
            "total_bursts": len(bursts),
        }

    async def get_anomaly_summary(
        self,
        user_id: Optional[str] = None,
    ) -> dict:
        usage_anomalies = await self.detect_usage_anomalies(user_id)
        burst_patterns = await self.detect_burst_patterns(user_id)

        all_anomalies = usage_anomalies["anomalies"] + burst_patterns["bursts"]

        critical = [a for a in all_anomalies if a.get("severity") == "critical"]
        warnings = [a for a in all_anomalies if a.get("severity") == "warning"]

        return {
            "summary": {
                "total_anomalies": len(all_anomalies),
                "critical": len(critical),
                "warnings": len(warnings),
                "status": "critical" if critical else ("warning" if warnings else "healthy"),
            },
            "critical": critical,
            "warnings": warnings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _calculate_std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
