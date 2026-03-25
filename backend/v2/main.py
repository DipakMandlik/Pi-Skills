from __future__ import annotations

from contextlib import asynccontextmanager
import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.v2.config import load_settings, validate_jwt_secret
from backend.v2.database.client import create_tables, init_engine
from backend.v2.middleware.error_handler import error_handler_middleware
from backend.v2.middleware.rate_limit import RateLimitMiddleware
from backend.v2.middleware.request_id import RequestIDMiddleware
from backend.v2.shared.logger import get_logger

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Skill Management Platform")
    settings = app.state.settings
    validate_jwt_secret(settings.jwt_secret)
    init_engine(settings)
    await create_tables()
    if settings.enable_bootstrap_seed:
        from backend.v2.database.seeds import seed_demo
        await seed_demo(settings)
    logger.info("Backend startup complete")
    yield
    logger.info("Shutting down backend")


def create_app() -> FastAPI:
    settings = load_settings()

    app = FastAPI(
        title="AI Skill Management Platform",
        version="2.0.0",
        description="Multi-tenant SaaS for creating, managing, assigning, and executing AI skills",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url="/api/redoc",
    )

    app.state.settings = settings

    app.middleware("http")(error_handler_middleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute, auth_requests_per_15min=settings.auth_rate_limit_per_15min)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    from backend.v2.modules.auth.routes import router as auth_router
    from backend.v2.modules.skills.routes import router as skills_router
    from backend.v2.modules.users.routes import router as users_router
    from backend.v2.modules.teams.routes import router as teams_router
    from backend.v2.modules.organizations.routes import router as org_router
    from backend.v2.modules.assignments.routes import router as assignments_router
    from backend.v2.modules.analytics.routes import router as analytics_router
    from backend.v2.modules.compat.routes import router as compat_router

    app.include_router(compat_router)
    app.include_router(auth_router)
    app.include_router(skills_router)
    app.include_router(users_router)
    app.include_router(teams_router)
    app.include_router(org_router)
    app.include_router(assignments_router)
    app.include_router(analytics_router)

    @app.get("/health")
    async def health():
        from backend.v2.database.client import _engine
        db_ok = False
        try:
            if _engine:
                async with _engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                    db_ok = True
        except Exception:
            pass
        return {"status": "ok" if db_ok else "degraded", "database": "connected" if db_ok else "disconnected", "uptime": int(time.time())}

    return app


app = create_app()


def run():
    settings = load_settings()
    uvicorn.run(
        "backend.v2.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    run()
