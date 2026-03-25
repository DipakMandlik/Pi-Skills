"""
Governance Copilot - Natural Language Interface for AI Governance
Enables querying governance data using natural language
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..services.subscription_service import SubscriptionService
from ..services.token_service import TokenService
from ..services.model_access_service import ModelAccessService
from ..services.ai_anomaly_detection import AnomalyDetectionEngine
from ..services.predictive_analytics import PredictiveAnalytics

logger = logging.getLogger("backend.governance_copilot")


class GovernanceCopilot:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.subscription_svc = SubscriptionService(db)
        self.token_svc = TokenService(db)
        self.model_access_svc = ModelAccessService(db)
        self.anomaly_engine = AnomalyDetectionEngine(db)
        self.analytics = PredictiveAnalytics(db)

    async def query(
        self,
        question: str,
        user_id: Optional[str] = None,
    ) -> dict:
        intent = self._detect_intent(question)
        entities = self._extract_entities(question)

        try:
            if intent == "usage_status":
                return await self._handle_usage_status(user_id, entities)
            elif intent == "cost_inquiry":
                return await self._handle_cost_inquiry(user_id, entities)
            elif intent == "subscription_info":
                return await self._handle_subscription_info(user_id)
            elif intent == "model_info":
                return await self._handle_model_info(entities)
            elif intent == "anomaly_check":
                return await self._handle_anomaly_check(user_id)
            elif intent == "forecast":
                return await self._handle_forecast(user_id)
            elif intent == "recommendation":
                return await self._handle_recommendation(user_id)
            elif intent == "plan_comparison":
                return await self._handle_plan_comparison()
            else:
                return await self._handle_general(question)
        except Exception as e:
            logger.error("Copilot query failed: %s", str(e))
            return {
                "intent": intent,
                "answer": f"I encountered an error processing your question. Please try rephrasing.",
                "error": str(e),
            }

    def _detect_intent(self, question: str) -> str:
        q = question.lower()

        if any(w in q for w in ["forecast", "predict", "estimate", "future", "project"]):
            return "forecast"
        elif any(w in q for w in ["how many tokens", "token usage", "tokens used", "remaining tokens"]):
            return "usage_status"
        elif any(w in q for w in ["cost", "spending", "budget", "expensive", "cheap"]):
            return "cost_inquiry"
        elif any(w in q for w in ["anomaly", "anomalies", "unusual", "spike", "problem", "issue"]):
            return "anomaly_check"
        elif any(w in q for w in ["plan", "subscription", "upgrade", "downgrade"]):
            if any(w in q for w in ["compare", "difference", "which"]):
                return "plan_comparison"
            return "subscription_info"
        elif any(w in q for w in ["model", "gpt", "claude", "gemini"]):
            return "model_info"
        elif any(w in q for w in ["recommend", "suggest", "advice", "optimize", "improve"]):
            return "recommendation"
        else:
            return "general"

    def _extract_entities(self, question: str) -> dict:
        entities = {}

        models = re.findall(r'(claude|gpt|gemini|llama)[\w\-\.]*', question.lower())
        if models:
            entities["models"] = models

        if "month" in question.lower():
            entities["period"] = "month"
        elif "week" in question.lower():
            entities["period"] = "week"
        elif "day" in question.lower():
            entities["period"] = "day"

        numbers = re.findall(r'\d+', question)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]

        return entities

    async def _handle_usage_status(
        self,
        user_id: Optional[str],
        entities: dict,
    ) -> dict:
        if not user_id:
            return {
                "intent": "usage_status",
                "answer": "Please provide a user ID to check token usage.",
            }

        usage = await self.token_svc.get_user_token_usage(user_id)

        if not usage:
            return {
                "intent": "usage_status",
                "answer": "No token usage data found for this period. Token tracking begins after your first AI request.",
            }

        pct = (usage["tokens_used"] / usage["tokens_limit"] * 100) if usage["tokens_limit"] > 0 else 0

        return {
            "intent": "usage_status",
            "answer": f"You've used {usage['tokens_used']:,} of {usage['tokens_limit']:,} tokens this period ({pct:.1f}%). You have {usage['remaining_tokens']:,} tokens remaining.",
            "data": usage,
        }

    async def _handle_cost_inquiry(
        self,
        user_id: Optional[str],
        entities: dict,
    ) -> dict:
        if not user_id:
            return {"intent": "cost_inquiry", "answer": "Please provide a user ID."}

        usage = await self.token_svc.get_user_token_usage(user_id)

        if not usage:
            return {"intent": "cost_inquiry", "answer": "No cost data available yet."}

        return {
            "intent": "cost_inquiry",
            "answer": f"Your accumulated cost this period is ${usage['cost_accumulated']:.4f}.",
            "data": usage,
        }

    async def _handle_subscription_info(self, user_id: Optional[str]) -> dict:
        if not user_id:
            return {"intent": "subscription_info", "answer": "Please provide a user ID."}

        plan = await self.subscription_svc.get_user_plan(user_id)

        if not plan:
            return {"intent": "subscription_info", "answer": "No active subscription found."}

        return {
            "intent": "subscription_info",
            "answer": f"You're on the {plan['display_name']} plan with {plan['monthly_token_limit']:,} tokens/month. You have access to {len(plan['allowed_models'])} models.",
            "data": plan,
        }

    async def _handle_model_info(self, entities: dict) -> dict:
        configs = await self.model_access_svc.list_model_access_configs()

        if not configs:
            return {"intent": "model_info", "answer": "No model configurations found."}

        model_list = ", ".join(c["model_id"] for c in configs)
        return {
            "intent": "model_info",
            "answer": f"There are {len(configs)} configured models: {model_list}. All are enabled and accessible.",
            "data": configs,
        }

    async def _handle_anomaly_check(self, user_id: Optional[str]) -> dict:
        summary = await self.anomaly_engine.get_anomaly_summary(user_id)

        status = summary["summary"]["status"]
        critical = summary["summary"]["critical"]
        warnings = summary["summary"]["warnings"]

        if status == "critical":
            answer = f"Found {critical} critical anomalies and {warnings} warnings. Immediate attention required."
        elif status == "warning":
            answer = f"Found {warnings} warnings. No critical issues detected."
        else:
            answer = "System is healthy. No anomalies detected."

        return {
            "intent": "anomaly_check",
            "answer": answer,
            "data": summary,
        }

    async def _handle_forecast(self, user_id: Optional[str]) -> dict:
        if not user_id:
            return {"intent": "forecast", "answer": "Please provide a user ID."}

        forecast = await self.analytics.forecast_monthly_cost(user_id)

        if not forecast["forecast"]:
            return {"intent": "forecast", "answer": "Insufficient data for forecasting."}

        next_month = forecast["forecast"][0]
        return {
            "intent": "forecast",
            "answer": f"Projected cost for next month: ${next_month['projected_cost']:.2f} (range: ${next_month['lower_bound']:.2f} - ${next_month['upper_bound']:.2f}). Monthly growth rate: {forecast['monthly_growth_rate']:.1f}%.",
            "data": forecast,
        }

    async def _handle_recommendation(self, user_id: Optional[str]) -> dict:
        if not user_id:
            return {"intent": "recommendation", "answer": "Please provide a user ID."}

        recs = await self.analytics.get_usage_recommendations(user_id)

        if not recs:
            return {"intent": "recommendation", "answer": "No recommendations at this time. Your usage patterns look good."}

        top = recs[0]
        return {
            "intent": "recommendation",
            "answer": f"Top recommendation ({top['priority']} priority): {top['title']}. {top['description']}",
            "data": recs,
        }

    async def _handle_plan_comparison(self) -> dict:
        plans = await self.subscription_svc.list_subscriptions()

        if not plans:
            return {"intent": "plan_comparison", "answer": "No subscription plans available."}

        summary = []
        for p in sorted(plans, key=lambda x: x["monthly_token_limit"]):
            summary.append(f"{p['display_name']}: {p['monthly_token_limit']:,} tokens/mo, ${p['cost_budget_monthly']}/mo budget")

        return {
            "intent": "plan_comparison",
            "answer": "Available plans:\n" + "\n".join(summary),
            "data": plans,
        }

    async def _handle_general(self, question: str) -> dict:
        return {
            "intent": "general",
            "answer": "I can help you with: token usage, costs, subscriptions, model info, anomaly detection, forecasts, and recommendations. Try asking about any of these topics.",
            "suggestions": [
                "How many tokens have I used this month?",
                "What's my current cost?",
                "Show me my subscription details",
                "Are there any anomalies in my usage?",
                "What's my cost forecast?",
                "Any recommendations to optimize?",
                "Compare available plans",
            ],
        }
