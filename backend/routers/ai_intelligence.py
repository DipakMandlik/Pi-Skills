"""
AI Intelligence Router - Exposes all AI-powered governance features
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..services.ai_anomaly_detection import AnomalyDetectionEngine
from ..services.smart_router import SmartModelRouter
from ..services.prompt_optimizer import PromptOptimizer
from ..services.predictive_analytics import PredictiveAnalytics
from ..services.content_safety import content_safety
from ..services.semantic_cache import semantic_cache
from ..services.governance_copilot import GovernanceCopilot
from ..services.auto_scaling import AutoScalingEngine
from ..services.subscription_service import SubscriptionService

logger = logging.getLogger("backend.ai_router")

router = APIRouter(prefix="/ai-intelligence", tags=["ai-intelligence"])


def _require_admin(request: Request):
    user = request.state.user
    role = str(getattr(user, "role", "")).upper()
    if role not in {"ORG_ADMIN", "SECURITY_ADMIN", "ADMIN"}:
        raise HTTPException(
            status_code=403,
            detail={"status": 403, "title": "Access Denied", "detail": "Admin role required"},
        )
    return user


# ── Anomaly Detection ───────────────────────────────────────────────

@router.get("/anomalies/summary")
async def get_anomaly_summary(
    request: Request,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = AnomalyDetectionEngine(db)
    return await engine.get_anomaly_summary(user_id)


@router.get("/anomalies/usage")
async def get_usage_anomalies(
    request: Request,
    user_id: str | None = None,
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = AnomalyDetectionEngine(db)
    return await engine.detect_usage_anomalies(user_id, hours)


@router.get("/anomalies/bursts")
async def get_burst_patterns(
    request: Request,
    user_id: str | None = None,
    window_minutes: int = Query(default=5, ge=1, le=60),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = AnomalyDetectionEngine(db)
    return await engine.detect_burst_patterns(user_id, window_minutes)


@router.get("/anomalies/cost-trends/{user_id}")
async def get_cost_trend_anomalies(
    user_id: str,
    request: Request,
    days: int = Query(default=30, ge=7, le=365),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = AnomalyDetectionEngine(db)
    return await engine.detect_cost_trend_anomalies(user_id, days)


# ── Smart Model Router ──────────────────────────────────────────────

@router.post("/smart-route/analyze")
async def analyze_task_complexity(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    router_svc = SmartModelRouter(db)
    return router_svc.analyze_task_complexity(body.get("prompt", ""))


@router.post("/smart-route/select")
async def select_optimal_model(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    router_svc = SmartModelRouter(db)
    sub_svc = SubscriptionService(db)

    user_id = body.get("user_id", "")
    plan = await sub_svc.get_user_plan(user_id)
    allowed_models = plan.get("allowed_models", []) if plan else []

    return await router_svc.select_optimal_model(
        prompt=body.get("prompt", ""),
        allowed_models=allowed_models,
        strategy=body.get("strategy", "balanced"),
        max_cost_per_request=body.get("max_cost_per_request"),
    )


@router.post("/smart-route/suggest-downgrade")
async def suggest_model_downgrade(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    router_svc = SmartModelRouter(db)
    return await router_svc.suggest_model_downgrade(
        current_model=body.get("current_model", ""),
        prompt=body.get("prompt", ""),
    )


@router.post("/smart-route/suggest-upgrade")
async def suggest_model_upgrade(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    router_svc = SmartModelRouter(db)
    return await router_svc.suggest_model_upgrade(
        current_model=body.get("current_model", ""),
        prompt=body.get("prompt", ""),
    )


@router.post("/smart-route/cost-comparison")
async def get_cost_comparison(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    router_svc = SmartModelRouter(db)
    sub_svc = SubscriptionService(db)

    user_id = body.get("user_id", "")
    plan = await sub_svc.get_user_plan(user_id)
    allowed_models = plan.get("allowed_models", []) if plan else body.get("allowed_models", [])

    return await router_svc.get_cost_comparison(
        allowed_models=allowed_models,
        estimated_tokens=body.get("estimated_tokens", 1000),
    )


# ── Prompt Optimizer ────────────────────────────────────────────────

@router.post("/optimize/prompt")
async def optimize_prompt(
    request: Request,
    body: dict,
):
    _require_admin(request)
    optimizer = PromptOptimizer()
    return optimizer.optimize_prompt(
        prompt=body.get("prompt", ""),
        strategy=body.get("strategy", "balanced"),
        preserve_quality=body.get("preserve_quality", True),
    )


@router.post("/optimize/system-prompt")
async def analyze_system_prompt(
    request: Request,
    body: dict,
):
    _require_admin(request)
    optimizer = PromptOptimizer()
    return optimizer.suggest_system_prompt_optimization(body.get("system_prompt", ""))


@router.post("/optimize/batch")
async def batch_optimize(
    request: Request,
    body: dict,
):
    _require_admin(request)
    optimizer = PromptOptimizer()
    return optimizer.batch_optimize(
        prompts=body.get("prompts", []),
        strategy=body.get("strategy", "balanced"),
    )


# ── Predictive Analytics ────────────────────────────────────────────

@router.get("/analytics/forecast/{user_id}")
async def get_cost_forecast(
    user_id: str,
    request: Request,
    months: int = Query(default=3, ge=1, le=12),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    analytics = PredictiveAnalytics(db)
    return await analytics.forecast_monthly_cost(user_id, months)


@router.get("/analytics/runway/{user_id}")
async def get_token_runway(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    analytics = PredictiveAnalytics(db)

    from ..services.token_service import TokenService
    token_svc = TokenService(db)
    usage = await token_svc.get_user_token_usage(user_id)
    remaining = usage["remaining_tokens"] if usage else 0

    return await analytics.project_token_runway(user_id, remaining)


@router.get("/analytics/efficiency")
async def get_model_efficiency(
    request: Request,
    user_id: str | None = None,
    period: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    analytics = PredictiveAnalytics(db)
    return await analytics.analyze_model_efficiency(user_id, period)


@router.get("/analytics/recommendations/{user_id}")
async def get_usage_recommendations(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    analytics = PredictiveAnalytics(db)
    recs = await analytics.get_usage_recommendations(user_id)
    return {"recommendations": recs, "total": len(recs)}


# ── Content Safety ──────────────────────────────────────────────────

@router.post("/safety/moderate-prompt")
async def moderate_prompt(
    request: Request,
    body: dict,
):
    _require_admin(request)
    result = content_safety.moderate_prompt(
        prompt=body.get("prompt", ""),
        user_id=body.get("user_id"),
        strict_mode=body.get("strict_mode", False),
    )
    return {
        "risk_level": result.risk_level.value,
        "flags": result.flags,
        "categories": result.categories,
        "safe": result.safe,
        "action": result.action,
        "details": result.details,
    }


@router.post("/safety/moderate-response")
async def moderate_response(
    request: Request,
    body: dict,
):
    _require_admin(request)
    result = content_safety.moderate_response(
        response=body.get("response", ""),
        user_id=body.get("user_id"),
    )
    return {
        "risk_level": result.risk_level.value,
        "flags": result.flags,
        "categories": result.categories,
        "safe": result.safe,
        "action": result.action,
        "details": result.details,
    }


@router.post("/safety/sanitize")
async def sanitize_prompt(
    request: Request,
    body: dict,
):
    _require_admin(request)
    return {"sanitized": content_safety.sanitize_prompt(body.get("prompt", ""))}


@router.get("/safety/policy")
async def get_content_policy(
    request: Request,
):
    _require_admin(request)
    return content_safety.get_content_policy()


# ── Semantic Cache ──────────────────────────────────────────────────

@router.get("/cache/stats")
async def get_cache_stats(
    request: Request,
):
    _require_admin(request)
    return semantic_cache.get_cache_stats()


# ── Governance Copilot ──────────────────────────────────────────────

@router.post("/copilot/query")
async def copilot_query(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    copilot = GovernanceCopilot(db)
    return await copilot.query(
        question=body.get("question", ""),
        user_id=user.user_id,
    )


@router.post("/copilot/admin-query")
async def copilot_admin_query(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    copilot = GovernanceCopilot(db)
    return await copilot.query(
        question=body.get("question", ""),
        user_id=body.get("user_id"),
    )


# ── Auto-Scaling ────────────────────────────────────────────────────

@router.get("/scaling/analyze/{user_id}")
async def analyze_scaling(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = AutoScalingEngine(db)
    return await engine.analyze_user_for_scaling(user_id)


@router.get("/scaling/recommendations")
async def get_all_scaling_recommendations(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = AutoScalingEngine(db)
    recs = await engine.get_all_scaling_recommendations()
    return {"recommendations": recs, "total": len(recs)}


@router.get("/scaling/utilization")
async def get_plan_utilization(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = AutoScalingEngine(db)
    return await engine.get_plan_utilization_report()
