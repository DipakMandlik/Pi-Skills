from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import load_settings, validate_jwt_secret
from .core.database import init_engine
from .core.migrations import assert_schema_at_head
from .core.redis_client import init_redis
from .middleware.audit import AuditMiddleware
from .middleware.rbac_middleware import RBACAuthMiddleware
from .middleware.request_id import RequestIDMiddleware
from .routers import admin, ai_intelligence, auth, execute, governance, models, monitoring, orchestrate, rbac_admin, skills, users

settings = load_settings()

logging.basicConfig(
    level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("backend")


async def _sync_skill_registry_defaults(actor_id: str = "system-seed"):
    from sqlalchemy import select

    from .core.database import SkillDefinitionModel, SkillStateModel, _session_factory
    from .services.skill_registry import get_default_registry_items

    if _session_factory is None:
        return

    created_definitions = 0
    created_states = 0

    async with _session_factory() as db:
        defaults = get_default_registry_items()
        for item in defaults:
            existing_def_res = await db.execute(
                select(SkillDefinitionModel).where(
                    SkillDefinitionModel.skill_id == item.skill_id,
                    SkillDefinitionModel.version == item.version,
                )
            )
            existing_def = existing_def_res.scalar_one_or_none()
            if existing_def is None:
                db.add(
                    SkillDefinitionModel(
                        skill_id=item.skill_id,
                        version=item.version,
                        display_name=item.display_name,
                        description=item.description,
                        required_models=item.required_models,
                        input_schema=item.input_schema,
                        output_format=item.output_format,
                        execution_handler=item.execution_handler,
                        error_handling=item.error_handling,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )
                created_definitions += 1

            existing_state_res = await db.execute(
                select(SkillStateModel).where(
                    SkillStateModel.skill_id == item.skill_id,
                    SkillStateModel.version == item.version,
                )
            )
            existing_state = existing_state_res.scalar_one_or_none()
            if existing_state is None:
                db.add(
                    SkillStateModel(
                        skill_id=item.skill_id,
                        version=item.version,
                        is_enabled=item.is_enabled,
                        updated_by=actor_id,
                    )
                )
                created_states += 1

        if created_definitions or created_states:
            await db.commit()

    logger.info(
        "Skill registry seed sync complete: created_definitions=%s created_states=%s",
        created_definitions,
        created_states,
    )


async def _seed_data():
    from datetime import datetime, timezone
    from uuid import uuid4

    from sqlalchemy import select

    from .core.database import (
        ModelPermissionModel,
        ModelAccessControlModel,
        RegisteredModelModel,
        SkillAssignmentModel,
        SubscriptionModel,
        UserModel,
        UserSubscriptionModel,
        _session_factory,
    )

    if _session_factory is None:
        return

    async with _session_factory() as db:
        existing = await db.execute(select(RegisteredModelModel).limit(1))
        if existing.scalar_one_or_none() is None:
            model_defs = [
                RegisteredModelModel(model_id="claude-3-5-sonnet-20241022", display_name="Claude 3.5 Sonnet", provider="anthropic", tier="premium", is_available=True, max_tokens=8192, cost_per_1k_tokens=0.003),
                RegisteredModelModel(model_id="claude-3-haiku-20240307", display_name="Claude 3 Haiku", provider="anthropic", tier="standard", is_available=True, max_tokens=4096, cost_per_1k_tokens=0.00025),
                RegisteredModelModel(model_id="gemini-1.5-pro", display_name="Gemini 1.5 Pro", provider="google", tier="premium", is_available=True, max_tokens=8192, cost_per_1k_tokens=0.00125),
                RegisteredModelModel(model_id="gpt-4o", display_name="GPT-4o", provider="openai", tier="premium", is_available=True, max_tokens=4096, cost_per_1k_tokens=0.005),
            ]
            for m in model_defs:
                db.add(m)
            await db.commit()
            logger.info("Seeded registered models")

        existing_admin = await db.execute(
            select(UserModel).where(UserModel.email == "admin@platform.local")
        )
        if existing_admin.scalar_one_or_none() is None:
            from uuid import uuid4

            import bcrypt

            admin_id = str(uuid4())
            test_user_id = str(uuid4())
            security_id = str(uuid4())
            engineer_id = str(uuid4())
            analytics_id = str(uuid4())
            scientist_id = str(uuid4())
            business_id = str(uuid4())
            viewer_id = str(uuid4())
            agent_id = str(uuid4())

            pw_hash = lambda pw: bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            seed_users = [
                UserModel(id=admin_id, external_id="PIQLENS", email="admin@platform.local",
                          display_name="Platform Admin", platform_role="ORG_ADMIN", password_hash=pw_hash("admin123")),
                UserModel(id=test_user_id, external_id="user@platform.local", email="user@platform.local",
                          display_name="Test User", platform_role="BUSINESS_USER", password_hash=pw_hash("user123")),
                UserModel(id=security_id, external_id="security@platform.local", email="security@platform.local",
                          display_name="Security Admin", platform_role="SECURITY_ADMIN", password_hash=pw_hash("security123")),
                UserModel(id=engineer_id, external_id="engineer@platform.local", email="engineer@platform.local",
                          display_name="Data Engineer", platform_role="DATA_ENGINEER", password_hash=pw_hash("engineer123")),
                UserModel(id=analytics_id, external_id="analytics@platform.local", email="analytics@platform.local",
                          display_name="Analytics Engineer", platform_role="ANALYTICS_ENGINEER", password_hash=pw_hash("analytics123")),
                UserModel(id=scientist_id, external_id="scientist@platform.local", email="scientist@platform.local",
                          display_name="Data Scientist", platform_role="DATA_SCIENTIST", password_hash=pw_hash("scientist123")),
                UserModel(id=business_id, external_id="business@platform.local", email="business@platform.local",
                          display_name="Business User", platform_role="BUSINESS_USER", password_hash=pw_hash("business123")),
                UserModel(id=viewer_id, external_id="viewer@platform.local", email="viewer@platform.local",
                          display_name="Viewer", platform_role="VIEWER", password_hash=pw_hash("viewer123")),
                UserModel(id=agent_id, external_id="agent@platform.local", email="agent@platform.local",
                          display_name="System Agent", platform_role="SYSTEM_AGENT", password_hash=pw_hash("agent123")),
            ]
            for u in seed_users:
                db.add(u)
            await db.commit()
            logger.info("Seeded 9 default accounts (ORG_ADMIN through SYSTEM_AGENT)")

            existing_sub = await db.execute(select(SubscriptionModel).limit(1))
            if existing_sub.scalar_one_or_none() is None:
                subscription_defs = [
                    SubscriptionModel(
                        plan_name="free",
                        display_name="Free Plan",
                        monthly_token_limit=10000,
                        max_tokens_per_request=2048,
                        allowed_models=["claude-3-haiku-20240307"],
                        features=["basic_chat"],
                        priority="low",
                        rate_limit_per_minute=10,
                        cost_budget_monthly=5.0,
                        is_active=True,
                    ),
                    SubscriptionModel(
                        plan_name="standard",
                        display_name="Standard Plan",
                        monthly_token_limit=100000,
                        max_tokens_per_request=4096,
                        allowed_models=["claude-3-haiku-20240307", "gpt-4o"],
                        features=["basic_chat", "code_generation"],
                        priority="standard",
                        rate_limit_per_minute=30,
                        cost_budget_monthly=50.0,
                        is_active=True,
                    ),
                    SubscriptionModel(
                        plan_name="premium",
                        display_name="Premium Plan",
                        monthly_token_limit=500000,
                        max_tokens_per_request=8192,
                        allowed_models=["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "gemini-1.5-pro", "gpt-4o"],
                        features=["basic_chat", "code_generation", "advanced_reasoning", "analysis"],
                        priority="high",
                        rate_limit_per_minute=60,
                        cost_budget_monthly=200.0,
                        is_active=True,
                    ),
                    SubscriptionModel(
                        plan_name="enterprise",
                        display_name="Enterprise Plan",
                        monthly_token_limit=2000000,
                        max_tokens_per_request=16384,
                        allowed_models=["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "gemini-1.5-pro", "gpt-4o"],
                        features=["basic_chat", "code_generation", "advanced_reasoning", "analysis", "custom_models"],
                        priority="critical",
                        rate_limit_per_minute=120,
                        cost_budget_monthly=1000.0,
                        is_active=True,
                    ),
                ]
                for s in subscription_defs:
                    db.add(s)
                await db.commit()
                logger.info("Seeded subscription plans")

                user_sub = UserSubscriptionModel(
                    user_id=test_user_id,
                    plan_name="standard",
                    assigned_by=admin_id,
                    is_active=True,
                )
                db.add(user_sub)

                admin_sub = UserSubscriptionModel(
                    user_id=admin_id,
                    plan_name="enterprise",
                    assigned_by=admin_id,
                    is_active=True,
                )
                db.add(admin_sub)
                await db.commit()
                logger.info("Seeded user subscriptions")

            existing_access = await db.execute(select(ModelAccessControlModel).limit(1))
            if existing_access.scalar_one_or_none() is None:
                access_defs = [
                    ModelAccessControlModel(
                        model_id="claude-3-5-sonnet-20241022",
                        allowed_roles=["ORG_ADMIN", "DATA_ENGINEER", "ANALYTICS_ENGINEER", "DATA_SCIENTIST"],
                        max_tokens_per_request=8192,
                        enabled=True,
                        rate_limit_per_minute=30,
                    ),
                    ModelAccessControlModel(
                        model_id="claude-3-haiku-20240307",
                        allowed_roles=["ORG_ADMIN", "DATA_ENGINEER", "ANALYTICS_ENGINEER", "DATA_SCIENTIST", "BUSINESS_USER", "VIEWER"],
                        max_tokens_per_request=4096,
                        enabled=True,
                        rate_limit_per_minute=60,
                    ),
                    ModelAccessControlModel(
                        model_id="gemini-1.5-pro",
                        allowed_roles=["ORG_ADMIN", "DATA_ENGINEER", "ANALYTICS_ENGINEER", "DATA_SCIENTIST"],
                        max_tokens_per_request=8192,
                        enabled=True,
                        rate_limit_per_minute=30,
                    ),
                    ModelAccessControlModel(
                        model_id="gpt-4o",
                        allowed_roles=["ORG_ADMIN", "DATA_ENGINEER", "ANALYTICS_ENGINEER", "DATA_SCIENTIST"],
                        max_tokens_per_request=4096,
                        enabled=True,
                        rate_limit_per_minute=30,
                    ),
                ]
                for a in access_defs:
                    db.add(a)
                await db.commit()
                logger.info("Seeded model access controls")

        # Ensure baseline permissions for test execution flows even on existing DBs.
        admin_res = await db.execute(select(UserModel).where(UserModel.email == "admin@platform.local"))
        user_res = await db.execute(select(UserModel).where(UserModel.email == "user@platform.local"))
        admin_user = admin_res.scalar_one_or_none()
        test_user = user_res.scalar_one_or_none()

        if admin_user and test_user:
            seeded_any = False
            now = datetime.now(timezone.utc)

            skill_res = await db.execute(
                select(SkillAssignmentModel).where(
                    SkillAssignmentModel.user_id == test_user.id,
                    SkillAssignmentModel.skill_id == "skill_summarizer",
                )
            )
            skill_assignment = skill_res.scalar_one_or_none()
            if skill_assignment is None:
                db.add(
                    SkillAssignmentModel(
                        id=str(uuid4()),
                        user_id=test_user.id,
                        skill_id="skill_summarizer",
                        assigned_by=admin_user.id,
                        assigned_at=now,
                        is_active=True,
                    )
                )
                seeded_any = True
            elif not skill_assignment.is_active:
                skill_assignment.is_active = True
                skill_assignment.revoked_by = None
                skill_assignment.revoked_at = None
                skill_assignment.assigned_by = admin_user.id
                seeded_any = True

            model_perm_res = await db.execute(
                select(ModelPermissionModel).where(
                    ModelPermissionModel.user_id == test_user.id,
                    ModelPermissionModel.model_id == "claude-3-haiku-20240307",
                )
            )
            model_perm = model_perm_res.scalar_one_or_none()
            if model_perm is None:
                db.add(
                    ModelPermissionModel(
                        id=str(uuid4()),
                        user_id=test_user.id,
                        model_id="claude-3-haiku-20240307",
                        granted_by=admin_user.id,
                        granted_at=now,
                        is_active=True,
                        notes="Baseline test permission",
                    )
                )
                seeded_any = True
            elif not model_perm.is_active:
                model_perm.is_active = True
                model_perm.revoked_by = None
                model_perm.revoked_at = None
                model_perm.granted_by = admin_user.id
                seeded_any = True

            if seeded_any:
                await db.commit()
                logger.info("Ensured baseline skill/model permissions for user@platform.local")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Governance Platform backend")
    validate_jwt_secret(settings.jwt_secret)
    init_engine(settings)
    init_redis(settings.redis_url)
    await assert_schema_at_head()
    await _sync_skill_registry_defaults()
    if settings.enable_bootstrap_seed:
        app_env = os.getenv("APP_ENV", "development").strip().lower()
        if app_env not in {"development", "dev", "test", "testing"}:
            raise RuntimeError("ENABLE_BOOTSTRAP_SEED is not allowed outside dev/test environments")
        logger.warning("Bootstrap seed is enabled; this should only be used in non-production environments.")
        await _seed_data()
    else:
        logger.info("Bootstrap seed disabled; no synthetic data will be inserted.")
    logger.info("Backend startup complete")
    yield
    logger.info("Shutting down backend")


app = FastAPI(
    title="AI Governance Platform",
    version="1.0.0",
    description="Policy enforcement engine for AI model access control",
    lifespan=lifespan,
)

app.add_middleware(AuditMiddleware)
app.add_middleware(RBACAuthMiddleware, settings=settings)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(skills.router)
app.include_router(models.router)
app.include_router(execute.router)
app.include_router(monitoring.router)
app.include_router(users.router)
app.include_router(governance.router)
app.include_router(admin.router)
app.include_router(rbac_admin.router)
app.include_router(ai_intelligence.router)
app.include_router(orchestrate.router)


@app.get("/health")
async def health():
    from sqlalchemy import text

    from .core.database import _engine
    from .core.redis_client import _use_redis, get_redis

    db_ok = False
    redis_ok = False

    try:
        if _engine:
            async with _engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                db_ok = True
    except Exception:
        pass

    if _use_redis:
        try:
            r = get_redis()
            await r.ping()
            redis_ok = True
        except Exception:
            pass
    else:
        redis_ok = True  # In-memory mode is always "ok"

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else ("in-memory" if not _use_redis else "disconnected"),
    }


def run():
    uvicorn.run(
        "backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    run()
