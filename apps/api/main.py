from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.core.config import Settings, load_settings, validate_jwt_secret
from apps.api.core.database import create_tables, init_engine
from apps.api.core.redis_client import init_redis
from apps.api.middleware.audit import AuditMiddleware
from apps.api.middleware.auth import JWTAuthMiddleware
from apps.api.middleware.request_id import RequestIDMiddleware
from apps.api.routers import auth, execute, models, monitoring, skills, users

settings = load_settings()

logging.basicConfig(
    level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("api")


async def _seed_data():
    from sqlalchemy import select
    from apps.api.core.database import RegisteredModelModel, UserModel
    from apps.api.core.database import _session_factory

    if _session_factory is None:
        return

    async with _session_factory() as db:
        existing = await db.execute(select(RegisteredModelModel).limit(1))
        if existing.scalar_one_or_none() is None:
            model_defs = [
                RegisteredModelModel(model_id="claude-3-5-sonnet-20241022", display_name="Claude 3.5 Sonnet", provider="anthropic", tier="premium", is_available=True, max_tokens=8192),
                RegisteredModelModel(model_id="claude-3-haiku-20240307", display_name="Claude 3 Haiku", provider="anthropic", tier="standard", is_available=True, max_tokens=4096),
                RegisteredModelModel(model_id="gemini-1.5-pro", display_name="Gemini 1.5 Pro", provider="google", tier="premium", is_available=True, max_tokens=8192),
                RegisteredModelModel(model_id="gpt-4o", display_name="GPT-4o", provider="openai", tier="premium", is_available=True, max_tokens=4096),
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

            admin = UserModel(
                id=str(uuid4()),
                external_id="admin@platform.local",
                email="admin@platform.local",
                display_name="Platform Admin",
                platform_role="admin",
                password_hash=bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            )
            db.add(admin)

            test_user = UserModel(
                id=str(uuid4()),
                external_id="user@platform.local",
                email="user@platform.local",
                display_name="Test User",
                platform_role="user",
                password_hash=bcrypt.hashpw("user123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            )
            db.add(test_user)
            
            # Create viewer user
            viewer_user = UserModel(
                id=str(uuid4()),
                external_id="viewer@platform.local",
                email="viewer@platform.local",
                display_name="Test Viewer",
                platform_role="viewer",
                password_hash=bcrypt.hashpw("viewer123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            )
            db.add(viewer_user)
            await db.commit()
            logger.info("Seeded default admin, user and viewer accounts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Governance Platform backend")
    validate_jwt_secret(settings.jwt_secret)
    init_engine(settings)
    init_redis(settings.redis_url)
    if settings.app_env in {"development", "dev", "test", "testing"}:
        await create_tables()
        logger.info("Runtime table creation enabled for dev/test environment")
    else:
        logger.info("Runtime table creation disabled outside dev/test; apply migrations before startup")
    if settings.enable_bootstrap_seed:
        if settings.app_env not in {"development", "dev", "test", "testing"}:
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
app.add_middleware(JWTAuthMiddleware, settings=settings)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.apps_api_auth_routes_enabled:
    app.include_router(auth.router)
else:
    logger.warning("apps/api deprecated auth router is disabled (APPS_API_AUTH_ROUTES_ENABLED=false).")
app.include_router(skills.router)
app.include_router(models.router)
app.include_router(execute.router)
app.include_router(monitoring.router)
app.include_router(users.router)


@app.get("/health")
async def health():
    from sqlalchemy import text
    from apps.api.core.redis_client import get_redis, _use_redis
    from apps.api.core.database import _engine

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
        "apps.api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    run()
