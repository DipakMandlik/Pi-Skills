"""
Admin Router - Complete governance admin endpoints
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..schemas.api import (
    SubscriptionCreateRequest,
    SubscriptionUpdateRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    SubscriptionAssignRequest,
    SubscriptionAssignResponse,
    SubscriptionDeleteResponse,
    UserSubscriptionListResponse,
    UserSubscriptionListItem,
    ModelAccessControlRequest,
    ModelAccessControlResponse,
    ModelAccessControlListResponse,
    FeatureFlagRequest,
    FeatureFlagResponse,
    SystemOverviewResponse,
    BudgetAlertResponse,
    UsageTrendResponse,
    GlobalStatsResponse,
    TokenResetRequest,
    TokenResetResponse,
    UsageLogsResponse,
    PolicyCreateRequest,
    PolicyUpdateRequest,
    PolicyResponse,
    PolicyListResponse,
    PolicyEvaluateRequest,
    PolicyEvaluateResponse,
    BulkUserAssignRequest,
    BulkUserAssignResponse,
    DeleteResponse,
)
from ..services.subscription_service import SubscriptionService
from ..services.model_access_service import ModelAccessService
from ..services.routing_service import RoutingService
from ..services.governance_service import GovernanceService
from ..services.token_service import TokenService
from ..services.policy_engine import PolicyEngine

logger = logging.getLogger("backend.admin_router")

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_settings():
    from ..main import settings
    return settings


def _require_admin(request: Request):
    user = request.state.user
    admin_roles = {"ORG_ADMIN", "SECURITY_ADMIN", "ADMIN"}
    user_roles = {r.upper() for r in user.roles}
    if not user_roles.intersection(admin_roles):
        raise HTTPException(
            status_code=403,
            detail={"status": 403, "title": "Access Denied", "detail": "Admin role required (ORG_ADMIN or SECURITY_ADMIN)"},
        )
    return user


# ── Subscription Management ──────────────────────────────────────────

@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    body: SubscriptionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    sub_svc = SubscriptionService(db)

    try:
        result = await sub_svc.create_subscription(
            plan_name=body.plan_name,
            display_name=body.display_name,
            monthly_token_limit=body.monthly_token_limit,
            max_tokens_per_request=body.max_tokens_per_request,
            allowed_models=body.allowed_models,
            features=body.features,
            priority=body.priority,
            rate_limit_per_minute=body.rate_limit_per_minute,
            cost_budget_monthly=body.cost_budget_monthly,
        )
        return SubscriptionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"status": 409, "title": "Conflict", "detail": str(e)})


@router.get("/subscriptions", response_model=SubscriptionListResponse)
async def list_subscriptions(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    sub_svc = SubscriptionService(db)
    plans = await sub_svc.list_subscriptions()
    return SubscriptionListResponse(
        subscriptions=[SubscriptionResponse(**p) for p in plans],
        total=len(plans),
    )


@router.get("/subscriptions/{plan_name}", response_model=SubscriptionResponse)
async def get_subscription(
    plan_name: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    sub_svc = SubscriptionService(db)
    plans = await sub_svc.list_subscriptions()
    for p in plans:
        if p["plan_name"] == plan_name:
            return SubscriptionResponse(**p)
    raise HTTPException(
        status_code=404,
        detail={"status": 404, "title": "Not Found", "detail": f"Plan '{plan_name}' not found"},
    )


@router.put("/subscriptions/{plan_name}", response_model=SubscriptionResponse)
async def update_subscription(
    plan_name: str,
    body: SubscriptionUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    sub_svc = SubscriptionService(db)

    try:
        result = await sub_svc.update_subscription(
            plan_name=plan_name,
            display_name=body.display_name,
            monthly_token_limit=body.monthly_token_limit,
            max_tokens_per_request=body.max_tokens_per_request,
            allowed_models=body.allowed_models,
            features=body.features,
            priority=body.priority,
            rate_limit_per_minute=body.rate_limit_per_minute,
            cost_budget_monthly=body.cost_budget_monthly,
        )
        return SubscriptionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"status": 404, "title": "Not Found", "detail": str(e)})


@router.delete("/subscriptions/{plan_name}", response_model=SubscriptionDeleteResponse)
async def delete_subscription(
    plan_name: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    sub_svc = SubscriptionService(db)

    try:
        result = await sub_svc.delete_subscription(plan_name)
        return SubscriptionDeleteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"status": 404, "title": "Not Found", "detail": str(e)})


@router.post("/subscriptions/assign", response_model=SubscriptionAssignResponse)
async def assign_subscription(
    body: SubscriptionAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    admin = _require_admin(request)
    sub_svc = SubscriptionService(db)

    try:
        result = await sub_svc.assign_plan_to_user(
            user_id=body.user_id,
            plan_name=body.plan_name,
            assigned_by=admin.user_id,
        )
        return SubscriptionAssignResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"status": 404, "title": "Not Found", "detail": str(e)})


@router.post("/subscriptions/bulk-assign", response_model=BulkUserAssignResponse)
async def bulk_assign_subscription(
    body: BulkUserAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    admin = _require_admin(request)
    sub_svc = SubscriptionService(db)

    assigned = []
    failed = []

    for user_id in body.user_ids:
        try:
            await sub_svc.assign_plan_to_user(
                user_id=user_id,
                plan_name=body.plan_name,
                assigned_by=admin.user_id,
            )
            assigned.append(user_id)
        except ValueError as e:
            failed.append({"user_id": user_id, "error": str(e)})
        except Exception as e:
            failed.append({"user_id": user_id, "error": str(e)})

    return BulkUserAssignResponse(
        assigned=assigned,
        failed=failed,
        total=len(body.user_ids),
    )


@router.get("/subscriptions/user/{user_id}")
async def get_user_subscription(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    sub_svc = SubscriptionService(db)
    result = await sub_svc.get_user_plan_info(user_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"status": 404, "title": "Not Found", "detail": "No subscription found for user"},
        )
    return result


@router.get("/user-subscriptions", response_model=UserSubscriptionListResponse)
async def list_user_subscriptions(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    sub_svc = SubscriptionService(db)
    subs = await sub_svc.list_user_subscriptions()
    return UserSubscriptionListResponse(
        user_subscriptions=[UserSubscriptionListItem(**s) for s in subs],
        total=len(subs),
    )


# ── Model Access Control ─────────────────────────────────────────────

@router.post("/model-access", response_model=ModelAccessControlResponse)
async def set_model_access(
    body: ModelAccessControlRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    access_svc = ModelAccessService(db)
    result = await access_svc.set_model_access(
        model_id=body.model_id,
        allowed_roles=body.allowed_roles,
        max_tokens_per_request=body.max_tokens_per_request,
        enabled=body.enabled,
        rate_limit_per_minute=body.rate_limit_per_minute,
    )
    return ModelAccessControlResponse(**result)


@router.get("/model-access", response_model=ModelAccessControlListResponse)
async def list_model_access(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    access_svc = ModelAccessService(db)
    configs = await access_svc.list_model_access_configs()
    return ModelAccessControlListResponse(
        configs=[ModelAccessControlResponse(**c) for c in configs],
        total=len(configs),
    )


@router.get("/model-access/{model_id}", response_model=ModelAccessControlResponse)
async def get_model_access(
    model_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    access_svc = ModelAccessService(db)
    config = await access_svc.get_model_access_config(model_id)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail={"status": 404, "title": "Not Found", "detail": f"No access control for model '{model_id}'"},
        )
    return ModelAccessControlResponse(**config)


@router.delete("/model-access/{model_id}", response_model=DeleteResponse)
async def delete_model_access(
    model_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    access_svc = ModelAccessService(db)
    result = await access_svc.delete_model_access(model_id)
    return DeleteResponse(**result)


# ── Feature Flags ────────────────────────────────────────────────────

@router.post("/feature-flags", response_model=FeatureFlagResponse)
async def set_feature_flag(
    body: FeatureFlagRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    routing_svc = RoutingService(db)
    result = await routing_svc.set_feature_flag(
        feature_name=body.feature_name,
        model_id=body.model_id,
        enabled=body.enabled,
        enabled_for=body.enabled_for,
        config=body.config,
    )
    return FeatureFlagResponse(**result)


@router.get("/feature-flags")
async def list_feature_flags(
    request: Request,
    model_id: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    routing_svc = RoutingService(db)
    flags = await routing_svc.get_feature_flags(model_id)
    return {"flags": flags, "total": len(flags)}


@router.delete("/feature-flags/{feature_name}/{model_id}", response_model=DeleteResponse)
async def delete_feature_flag(
    feature_name: str,
    model_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    routing_svc = RoutingService(db)
    result = await routing_svc.delete_feature_flag(feature_name, model_id)
    return DeleteResponse(**result)


# ── Governance Policies ──────────────────────────────────────────────

@router.post("/policies", response_model=PolicyResponse)
async def create_policy(
    body: PolicyCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = PolicyEngine(db)

    try:
        result = await engine.create_policy(
            policy_name=body.policy_name,
            policy_type=body.policy_type,
            description=body.description,
            conditions=body.conditions,
            actions=body.actions,
            priority=body.priority,
            enabled=body.enabled,
        )
        return PolicyResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"status": 400, "title": "Bad Request", "detail": str(e)})


@router.get("/policies", response_model=PolicyListResponse)
async def list_policies(
    request: Request,
    policy_type: str | None = None,
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = PolicyEngine(db)
    policies = await engine.list_policies(policy_type=policy_type, enabled_only=enabled_only)
    return PolicyListResponse(
        policies=[PolicyResponse(**p) for p in policies],
        total=len(policies),
    )


@router.get("/policies/types")
async def get_policy_types(request: Request):
    _require_admin(request)
    return {"types": PolicyEngine.get_policy_types()}


@router.get("/policies/{policy_name}", response_model=PolicyResponse)
async def get_policy(
    policy_name: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = PolicyEngine(db)
    policy = await engine.get_policy(policy_name)
    if policy is None:
        raise HTTPException(
            status_code=404,
            detail={"status": 404, "title": "Not Found", "detail": f"Policy '{policy_name}' not found"},
        )
    return PolicyResponse(**policy)


@router.put("/policies/{policy_name}", response_model=PolicyResponse)
async def update_policy(
    policy_name: str,
    body: PolicyUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = PolicyEngine(db)

    try:
        result = await engine.update_policy(
            policy_name=policy_name,
            description=body.description,
            conditions=body.conditions,
            actions=body.actions,
            priority=body.priority,
            enabled=body.enabled,
        )
        return PolicyResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"status": 404, "title": "Not Found", "detail": str(e)})


@router.delete("/policies/{policy_name}", response_model=DeleteResponse)
async def delete_policy(
    policy_name: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = PolicyEngine(db)

    try:
        result = await engine.delete_policy(policy_name)
        return DeleteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"status": 404, "title": "Not Found", "detail": str(e)})


@router.post("/policies/evaluate", response_model=PolicyEvaluateResponse)
async def evaluate_policies(
    body: PolicyEvaluateRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    engine = PolicyEngine(db)
    result = await engine.evaluate_request(
        user_id=body.user_id,
        user_role=body.user_role,
        model_id=body.model_id,
        task_type=body.task_type,
        estimated_tokens=body.estimated_tokens,
        context=body.context,
    )
    return PolicyEvaluateResponse(**result)


# ── Token Management ─────────────────────────────────────────────────

@router.post("/tokens/reset", response_model=TokenResetResponse)
async def reset_user_tokens(
    body: TokenResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    token_svc = TokenService(db)
    result = await token_svc.reset_user_tokens(body.user_id, body.new_limit)
    return TokenResetResponse(**result)


@router.get("/tokens/budget-alert/{user_id}", response_model=BudgetAlertResponse)
async def get_budget_alert(
    user_id: str,
    request: Request,
    cost_budget: float = Query(default=100.0),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    token_svc = TokenService(db)
    result = await token_svc.check_budget_alert(user_id, cost_budget)
    return BudgetAlertResponse(**result)


@router.get("/tokens/trend/{user_id}", response_model=UsageTrendResponse)
async def get_usage_trend(
    user_id: str,
    request: Request,
    months: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    token_svc = TokenService(db)
    trend = await token_svc.get_usage_trend(user_id, months)
    return UsageTrendResponse(trend=trend, months=months)


@router.get("/tokens/global-stats", response_model=GlobalStatsResponse)
async def get_global_stats(
    request: Request,
    period: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    token_svc = TokenService(db)
    stats = await token_svc.get_global_usage_stats(period)
    return GlobalStatsResponse(**stats)


@router.get("/tokens/logs", response_model=UsageLogsResponse)
async def get_usage_logs(
    request: Request,
    user_id: str | None = None,
    model_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    token_svc = TokenService(db)
    result = await token_svc.get_usage_logs(user_id, model_id, limit, offset)
    return UsageLogsResponse(**result)


# ── System Overview ──────────────────────────────────────────────────

@router.get("/overview", response_model=SystemOverviewResponse)
async def system_overview(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    settings = _get_settings()
    governance = GovernanceService(settings, db)
    overview = await governance.get_system_overview()
    return SystemOverviewResponse(**overview)
