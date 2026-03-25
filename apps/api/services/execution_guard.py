from __future__ import annotations

import logging
import re
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings
from ..core.database import RegisteredModelModel
from ..core.redis_client import cache_get, cache_incr, cache_expire, cache_set
from ..models.domain import (
    AuthUser,
    GuardContext,
    GuardDenied,
    ModelInvocationError,
    ModelResult,
)
from .permission_service import resolve_user_permissions
from .audit_service import AuditService

logger = logging.getLogger("backend.execution_guard")

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"you are now",
    r"act as.*admin",
    r"reveal.*system prompt",
    r"bypass.*security",
    r"override.*policy",
    r"switch.*model",
    r"use.*gpt",
    r"use.*claude",
    r"use.*gemini",
    r"jailbreak",
    r"do anything now",
]


class ExecutionGuard:
    def __init__(self, settings: Settings, db: AsyncSession, model_adapter, audit: AuditService):
        self.settings = settings
        self.db = db
        self.model_adapter = model_adapter
        self.audit = audit

    async def execute(
        self,
        user: AuthUser,
        skill_id: str,
        model_id: str,
        prompt: str,
        parameters: Optional[dict] = None,
        max_tokens: int = 1000,
    ) -> ModelResult:
        ctx = GuardContext(
            user_id=user.user_id,
            role=user.role,
            skill_id=skill_id,
            model_id=model_id,
            request_id=user.request_id,
            started_at=time.monotonic(),
        )

        try:
            await self._assert_model_registered(ctx)
            await self._assert_skill_access(ctx)
            await self._assert_model_access(ctx)
            await self._assert_rate_limit(ctx)
            sanitized = await self._sanitize_prompt(prompt, ctx)

            result = await self.model_adapter.invoke(
                model_id=model_id,
                prompt=sanitized,
                parameters=parameters or {},
                max_tokens=max_tokens,
            )

            await self.audit.log_success(
                self.db, ctx, tokens_used=result.tokens_used, latency_ms=self._elapsed_ms(ctx)
            )
            return result

        except GuardDenied as e:
            await self.audit.log_denied(
                self.db, ctx, reason=e.reason, latency_ms=self._elapsed_ms(ctx)
            )
            raise

        except ModelInvocationError as e:
            await self.audit.log_error(
                self.db, ctx, error=str(e), latency_ms=self._elapsed_ms(ctx)
            )
            raise

    async def validate_all_gates(self, user: AuthUser, skill_id: str, model_id: str) -> GuardContext:
        ctx = GuardContext(
            user_id=user.user_id,
            role=user.role,
            skill_id=skill_id,
            model_id=model_id,
            request_id=user.request_id,
            started_at=time.monotonic(),
        )
        await self._assert_model_registered(ctx)
        await self._assert_skill_access(ctx)
        await self._assert_model_access(ctx)
        await self._assert_rate_limit(ctx)
        return ctx

    async def _assert_model_registered(self, ctx: GuardContext) -> None:
        cached = await cache_get(f"model:registered:{ctx.model_id}")
        if cached is not None:
            if cached.get("is_available"):
                return
            raise GuardDenied(
                reason="DENIED_MODEL_UNKNOWN",
                message=f"Model '{ctx.model_id}' is not available",
            )

        result = await self.db.execute(
            select(RegisteredModelModel).where(RegisteredModelModel.model_id == ctx.model_id)
        )
        model = result.scalar_one_or_none()

        if model is None or not model.is_available:
            raise GuardDenied(
                reason="DENIED_MODEL_UNKNOWN",
                message=f"Model '{ctx.model_id}' is not registered or unavailable",
            )

        await cache_set(
            f"model:registered:{ctx.model_id}",
            {"model_id": ctx.model_id, "is_available": True},
            self.settings.redis_model_ttl,
        )

    async def _assert_skill_access(self, ctx: GuardContext) -> None:
        perms = await resolve_user_permissions(ctx.user_id, self.db)
        if ctx.skill_id not in perms.allowed_skills:
            raise GuardDenied(
                reason="DENIED_SKILL",
                message=f"No active assignment for skill '{ctx.skill_id}'",
            )

    async def _assert_model_access(self, ctx: GuardContext) -> None:
        perms = await resolve_user_permissions(ctx.user_id, self.db)
        if ctx.model_id not in perms.allowed_models:
            raise GuardDenied(
                reason="DENIED_MODEL",
                message=f"No active permission for model '{ctx.model_id}'",
            )

    async def _assert_rate_limit(self, ctx: GuardContext) -> None:
        key = f"rate:{ctx.user_id}:{ctx.model_id}"
        count = await cache_incr(key)
        if count == 1:
            await cache_expire(key, self.settings.redis_rate_window)
        if count > self.settings.max_requests_per_minute:
            raise GuardDenied(
                reason="RATE_LIMITED",
                message="Rate limit exceeded for this model",
            )

    async def _sanitize_prompt(self, prompt: str, ctx: GuardContext) -> str:
        if len(prompt) > self.settings.max_prompt_length:
            raise GuardDenied(
                reason="PROMPT_TOO_LONG",
                message=f"Prompt exceeds {self.settings.max_prompt_length} characters",
            )

        prompt_lower = prompt.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, prompt_lower):
                await self.audit.log_security_event(self.db, ctx, "INJECTION_ATTEMPT_DETECTED")
                raise GuardDenied(
                    reason="PROMPT_POLICY_VIOLATION",
                    message="Prompt did not pass content policy",
                )

        return prompt.strip()

    def _elapsed_ms(self, ctx: GuardContext) -> int:
        return int((time.monotonic() - ctx.started_at) * 1000)
