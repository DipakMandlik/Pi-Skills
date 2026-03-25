"""
Governance Service - Main orchestrator for AI request governance
Coordinates subscription, token, model access, and routing services
"""
from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.model_adapter import get_adapter
from ..core.config import Settings
from ..core.redis_client import cache_incr, cache_expire, cache_get
from ..models.domain import AuthUser, GuardDenied, ModelResult
from .subscription_service import SubscriptionService
from .token_service import TokenService
from .model_access_service import ModelAccessService
from .routing_service import RoutingService
from .audit_service import AuditService

logger = logging.getLogger("backend.governance_service")


class GovernanceService:
    def __init__(self, settings: Settings, db: AsyncSession):
        self.settings = settings
        self.db = db
        self.subscription_svc = SubscriptionService(db)
        self.token_svc = TokenService(db)
        self.model_access_svc = ModelAccessService(db)
        self.routing_svc = RoutingService(db)
        self.audit_svc = AuditService()

    async def process_request(
        self,
        user: AuthUser,
        prompt: str,
        model_id: Optional[str] = None,
        task_type: str = "general",
        skill_id: Optional[str] = None,
        max_tokens: int = 1000,
        parameters: Optional[dict] = None,
    ) -> dict:
        request_id = str(uuid4())
        start_time = time.monotonic()

        try:
            plan = await self.subscription_svc.get_user_plan(user.user_id)
            if plan is None:
                raise GuardDenied(
                    reason="NO_SUBSCRIPTION",
                    message="No active subscription found",
                )

            estimated_tokens = self.token_svc.estimate_tokens(prompt) + max_tokens

            if estimated_tokens > plan["max_tokens_per_request"]:
                raise GuardDenied(
                    reason="TOKEN_LIMIT_EXCEEDED",
                    message=f"Request exceeds max tokens per request ({plan['max_tokens_per_request']})",
                )

            token_check = await self.token_svc.validate_tokens_available(
                user.user_id, estimated_tokens, plan["monthly_token_limit"]
            )
            if not token_check["allowed"]:
                raise GuardDenied(
                    reason=token_check["reason"],
                    message=token_check["message"],
                )

            route_result = await self.routing_svc.select_model(
                user_id=user.user_id,
                task_type=task_type,
                requested_model=model_id,
                allowed_models=plan.get("allowed_models", []),
                token_budget=max_tokens,
            )
            if not route_result["selected"]:
                raise GuardDenied(
                    reason=route_result["reason"],
                    message=route_result["message"],
                )

            selected_model = route_result["model_id"]

            access_result = await self.model_access_svc.validate_model_access(
                user.user_id, user.role, selected_model
            )
            if not access_result["allowed"]:
                raise GuardDenied(
                    reason=access_result["reason"],
                    message=access_result["message"],
                )

            effective_max_tokens = min(
                max_tokens,
                access_result.get("max_tokens_per_request", 4096),
                plan["max_tokens_per_request"],
            )

            await self._assert_rate_limit(user.user_id, selected_model)

            adapter = get_adapter(self.settings.model_adapter_type, self.settings)
            result = await adapter.invoke(
                model_id=selected_model,
                prompt=prompt,
                parameters=parameters or {},
                max_tokens=effective_max_tokens,
            )

            cost_per_1k = await self.token_svc.get_model_cost_per_1k(selected_model)
            cost = self.token_svc.calculate_cost(result.tokens_used, cost_per_1k)

            await self.token_svc.deduct_tokens(
                user_id=user.user_id,
                model_id=selected_model,
                tokens_used=result.tokens_used,
                cost=cost,
                request_id=request_id,
                skill_id=skill_id,
                latency_ms=int((time.monotonic() - start_time) * 1000),
                outcome="SUCCESS",
            )

            latency_ms = int((time.monotonic() - start_time) * 1000)
            await self.audit_svc.log_success(
                self.db,
                type("Ctx", (), {
                    "request_id": request_id,
                    "user_id": user.user_id,
                    "skill_id": skill_id or "governance",
                    "model_id": selected_model,
                })(),
                tokens_used=result.tokens_used,
                latency_ms=latency_ms,
            )

            return {
                "status": "success",
                "request_id": request_id,
                "result": result.content,
                "model_id": result.model_id,
                "tokens_used": result.tokens_used,
                "cost": cost,
                "latency_ms": latency_ms,
                "finish_reason": result.finish_reason,
                "remaining_tokens": token_check["remaining_tokens"] - result.tokens_used,
                "route_info": route_result,
            }

        except GuardDenied as e:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            await self.audit_svc.log_denied(
                self.db,
                type("Ctx", (), {
                    "request_id": request_id,
                    "user_id": user.user_id,
                    "skill_id": skill_id or "governance",
                    "model_id": model_id or "auto",
                })(),
                reason=e.reason,
                latency_ms=latency_ms,
            )
            return {
                "status": "denied",
                "request_id": request_id,
                "reason": e.reason,
                "message": e.message,
                "latency_ms": latency_ms,
            }

        except Exception as e:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("Governance request failed: %s", str(e))
            await self.audit_svc.log_error(
                self.db,
                type("Ctx", (), {
                    "request_id": request_id,
                    "user_id": user.user_id,
                    "skill_id": skill_id or "governance",
                    "model_id": model_id or "auto",
                })(),
                error=str(e),
                latency_ms=latency_ms,
            )
            return {
                "status": "error",
                "request_id": request_id,
                "error": str(e),
                "latency_ms": latency_ms,
            }

    async def validate_request(
        self,
        user: AuthUser,
        model_id: Optional[str] = None,
        task_type: str = "general",
        estimated_tokens: int = 1000,
    ) -> dict:
        plan = await self.subscription_svc.get_user_plan(user.user_id)
        if plan is None:
            return {
                "valid": False,
                "reason": "NO_SUBSCRIPTION",
                "message": "No active subscription found",
            }

        if estimated_tokens > plan["max_tokens_per_request"]:
            return {
                "valid": False,
                "reason": "TOKEN_LIMIT_EXCEEDED",
                "message": f"Request exceeds max tokens per request ({plan['max_tokens_per_request']})",
            }

        token_check = await self.token_svc.validate_tokens_available(
            user.user_id, estimated_tokens, plan["monthly_token_limit"]
        )
        if not token_check["allowed"]:
            return {
                "valid": False,
                "reason": token_check["reason"],
                "message": token_check["message"],
            }

        route_result = await self.routing_svc.select_model(
            user_id=user.user_id,
            task_type=task_type,
            requested_model=model_id,
            allowed_models=plan.get("allowed_models", []),
            token_budget=estimated_tokens,
        )
        if not route_result["selected"]:
            return {
                "valid": False,
                "reason": route_result["reason"],
                "message": route_result["message"],
            }

        selected_model = route_result["model_id"]
        access_result = await self.model_access_svc.validate_model_access(
            user.user_id, user.role, selected_model
        )
        if not access_result["allowed"]:
            return {
                "valid": False,
                "reason": access_result["reason"],
                "message": access_result["message"],
            }

        return {
            "valid": True,
            "model_id": selected_model,
            "plan": plan,
            "token_usage": token_check,
            "route_info": route_result,
            "access_info": access_result,
        }

    async def _assert_rate_limit(self, user_id: str, model_id: str) -> None:
        key = f"governance:rate:{user_id}:{model_id}"
        count = await cache_incr(key)
        if count == 1:
            await cache_expire(key, 60)
        if count > self.settings.max_requests_per_minute:
            raise GuardDenied(
                reason="RATE_LIMITED",
                message="Rate limit exceeded for this model",
            )

    async def get_user_dashboard(self, user_id: str) -> dict:
        plan = await self.subscription_svc.get_user_plan(user_id)
        token_usage = await self.token_svc.get_user_token_usage(user_id)
        stats = await self.token_svc.get_token_usage_stats(user_id)

        return {
            "user_id": user_id,
            "subscription": plan,
            "token_usage": token_usage,
            "usage_stats": stats,
        }

    async def get_system_overview(self) -> dict:
        subscriptions = await self.subscription_svc.list_subscriptions()
        model_configs = await self.model_access_svc.list_model_access_configs()

        return {
            "subscriptions": subscriptions,
            "model_access_configs": model_configs,
            "total_subscriptions": len(subscriptions),
            "total_models_configured": len(model_configs),
        }
