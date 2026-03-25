"""
Smart Model Router - AI-driven model selection with cost optimization
Uses task complexity analysis and cost/quality tradeoff optimization
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import RegisteredModelModel
from ..core.redis_client import cache_get, cache_set

logger = logging.getLogger("backend.smart_router")


class TaskComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


class SmartModelRouter:
    def __init__(self, db: AsyncSession):
        self.db = db

    def analyze_task_complexity(self, prompt: str) -> dict:
        word_count = len(prompt.split())
        char_count = len(prompt)

        has_code = bool(re.search(r'```|def |class |function |import |from ', prompt))
        has_math = bool(re.search(r'\d+\s*[\+\-\*\/\=]\s*\d+|calculate|solve|equation', prompt, re.I))
        has_reasoning = bool(re.search(r'why|explain|analyze|compare|evaluate|reason|think|step.by.step', prompt, re.I))
        has_creative = bool(re.search(r'write|create|story|poem|generate|design|brainstorm', prompt, re.I))
        has_data = bool(re.search(r'json|csv|sql|table|data|parse|format|extract', prompt, re.I))
        has_translation = bool(re.search(r'translate|translation|language', prompt, re.I))

        complexity_score = 0
        if word_count > 500:
            complexity_score += 3
        elif word_count > 200:
            complexity_score += 2
        elif word_count > 50:
            complexity_score += 1

        if has_code:
            complexity_score += 3
        if has_math:
            complexity_score += 2
        if has_reasoning:
            complexity_score += 2
        if has_data:
            complexity_score += 1
        if has_translation:
            complexity_score += 1

        if complexity_score <= 2:
            complexity = TaskComplexity.SIMPLE
        elif complexity_score <= 5:
            complexity = TaskComplexity.MODERATE
        elif complexity_score <= 8:
            complexity = TaskComplexity.COMPLEX
        else:
            complexity = TaskComplexity.CRITICAL

        return {
            "complexity": complexity.value,
            "score": complexity_score,
            "word_count": word_count,
            "char_count": char_count,
            "features": {
                "has_code": has_code,
                "has_math": has_math,
                "has_reasoning": has_reasoning,
                "has_creative": has_creative,
                "has_data": has_data,
                "has_translation": has_translation,
            },
        }

    async def select_optimal_model(
        self,
        prompt: str,
        allowed_models: list[str],
        strategy: str = "balanced",
        max_cost_per_request: Optional[float] = None,
    ) -> dict:
        analysis = self.analyze_task_complexity(prompt)
        complexity = analysis["complexity"]

        models = await self._get_models_with_costs(allowed_models)
        if not models:
            return {
                "selected": False,
                "reason": "NO_MODELS_AVAILABLE",
                "analysis": analysis,
            }

        if strategy == "cost_optimized":
            selected = self._select_cost_optimized(models, complexity)
        elif strategy == "quality_optimized":
            selected = self._select_quality_optimized(models, complexity)
        elif strategy == "balanced":
            selected = self._select_balanced(models, complexity)
        else:
            selected = self._select_balanced(models, complexity)

        if max_cost_per_request and selected:
            estimated_cost = self._estimate_cost(
                analysis["word_count"],
                selected.get("cost_per_1k", 0),
            )
            if estimated_cost > max_cost_per_request:
                cheaper = [m for m in models if m["cost_per_1k"] < selected["cost_per_1k"]]
                if cheaper:
                    selected = min(cheaper, key=lambda m: m["cost_per_1k"])

        return {
            "selected": selected is not None,
            "model": selected,
            "analysis": analysis,
            "strategy": strategy,
            "alternatives": [m for m in models if m != selected][:3],
        }

    async def suggest_model_downgrade(
        self,
        current_model: str,
        prompt: str,
    ) -> dict:
        analysis = self.analyze_task_complexity(prompt)
        complexity = analysis["complexity"]

        if complexity in [TaskComplexity.SIMPLE, TaskComplexity.MODERATE]:
            models = await self._get_all_models()
            current = next((m for m in models if m["model_id"] == current_model), None)

            if current and current["tier"] == "premium":
                standard_models = [m for m in models if m["tier"] == "standard" and m["is_available"]]
                if standard_models:
                    suggestion = standard_models[0]
                    current_cost = current.get("cost_per_1k", 0)
                    suggestion_cost = suggestion.get("cost_per_1k", 0)
                    savings_pct = ((current_cost - suggestion_cost) / current_cost * 100) if current_cost > 0 else 0

                    return {
                        "suggestion": True,
                        "current_model": current_model,
                        "suggested_model": suggestion["model_id"],
                        "reason": f"Task is {complexity.value} complexity - standard model sufficient",
                        "estimated_savings_pct": round(savings_pct, 1),
                        "quality_impact": "low",
                    }

        return {
            "suggestion": False,
            "reason": f"Task complexity ({complexity.value}) requires current model tier",
        }

    async def suggest_model_upgrade(
        self,
        current_model: str,
        prompt: str,
    ) -> dict:
        analysis = self.analyze_task_complexity(prompt)
        complexity = analysis["complexity"]

        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]:
            models = await self._get_all_models()
            current = next((m for m in models if m["model_id"] == current_model), None)

            if current and current["tier"] == "standard":
                premium_models = [m for m in models if m["tier"] == "premium" and m["is_available"]]
                if premium_models:
                    suggestion = premium_models[0]
                    return {
                        "suggestion": True,
                        "current_model": current_model,
                        "suggested_model": suggestion["model_id"],
                        "reason": f"Task is {complexity.value} complexity - premium model recommended",
                        "quality_improvement": "significant",
                        "features_detected": analysis["features"],
                    }

        return {"suggestion": False, "reason": "Current model is appropriate"}

    async def get_cost_comparison(
        self,
        allowed_models: list[str],
        estimated_tokens: int,
    ) -> dict:
        models = await self._get_models_with_costs(allowed_models)
        comparisons = []

        for model in models:
            cost = self._estimate_cost_tokens(estimated_tokens, model["cost_per_1k"])
            comparisons.append({
                "model_id": model["model_id"],
                "display_name": model["display_name"],
                "tier": model["tier"],
                "cost_per_1k": model["cost_per_1k"],
                "estimated_cost": round(cost, 6),
                "provider": model["provider"],
            })

        comparisons.sort(key=lambda x: x["estimated_cost"])

        cheapest = comparisons[0] if comparisons else None
        most_expensive = comparisons[-1] if comparisons else None

        return {
            "comparisons": comparisons,
            "cheapest": cheapest,
            "most_expensive": most_expensive,
            "estimated_tokens": estimated_tokens,
            "max_savings": round(
                most_expensive["estimated_cost"] - cheapest["estimated_cost"], 6
            ) if cheapest and most_expensive else 0,
        }

    async def _get_models_with_costs(self, allowed_models: list[str]) -> list[dict]:
        result = await self.db.execute(
            select(RegisteredModelModel).where(
                RegisteredModelModel.model_id.in_(allowed_models),
                RegisteredModelModel.is_available == True,
            ).order_by(RegisteredModelModel.tier.desc())
        )
        models = result.scalars().all()
        return [
            {
                "model_id": m.model_id,
                "display_name": m.display_name,
                "provider": m.provider,
                "tier": m.tier,
                "max_tokens": m.max_tokens,
                "cost_per_1k": m.cost_per_1k_tokens or 0.0,
                "is_available": m.is_available,
            }
            for m in models
        ]

    async def _get_all_models(self) -> list[dict]:
        result = await self.db.execute(
            select(RegisteredModelModel).where(
                RegisteredModelModel.is_available == True
            )
        )
        models = result.scalars().all()
        return [
            {
                "model_id": m.model_id,
                "display_name": m.display_name,
                "provider": m.provider,
                "tier": m.tier,
                "max_tokens": m.max_tokens,
                "cost_per_1k": m.cost_per_1k_tokens or 0.0,
                "is_available": m.is_available,
            }
            for m in models
        ]

    def _select_cost_optimized(self, models: list[dict], complexity: str) -> Optional[dict]:
        if complexity in ["simple", "moderate"]:
            standard = [m for m in models if m["tier"] == "standard"]
            if standard:
                return min(standard, key=lambda m: m["cost_per_1k"])

        return min(models, key=lambda m: m["cost_per_1k"])

    def _select_quality_optimized(self, models: list[dict], complexity: str) -> Optional[dict]:
        premium = [m for m in models if m["tier"] == "premium"]
        if premium:
            return premium[0]
        return models[0] if models else None

    def _select_balanced(self, models: list[dict], complexity: str) -> Optional[dict]:
        if complexity == "simple":
            cheap = [m for m in models if m["tier"] == "standard"]
            if cheap:
                return min(cheap, key=lambda m: m["cost_per_1k"])
        elif complexity in ["complex", "critical"]:
            premium = [m for m in models if m["tier"] == "premium"]
            if premium:
                return min(premium, key=lambda m: m["cost_per_1k"])

        return models[0] if models else None

    def _estimate_cost(self, word_count: int, cost_per_1k: float) -> float:
        tokens = word_count * 1.3
        return (tokens / 1000) * cost_per_1k

    def _estimate_cost_tokens(self, tokens: int, cost_per_1k: float) -> float:
        return (tokens / 1000) * cost_per_1k
