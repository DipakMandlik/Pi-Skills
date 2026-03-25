from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")


def _to_int(name: str, fallback: int) -> int:
    raw = os.getenv(name, str(fallback)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


def _to_bool(name: str, fallback: bool) -> bool:
    raw = os.getenv(name, str(fallback)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def validate_jwt_secret(secret: str) -> None:
    if not secret:
        raise ValueError("JWT_SECRET must be set")
    if secret == "change-me-in-production-please":
        raise ValueError("JWT_SECRET must not use the insecure default value")
    if len(secret) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters")


@dataclass(frozen=True)
class Settings:
    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    debug: bool = False

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Service-boundary consolidation: route auth to canonical backend service.
    governance_backend_url: str = "http://localhost:8000"
    apps_api_auth_proxy_enabled: bool = True
    apps_api_auth_routes_enabled: bool = True
    governance_auth_timeout_seconds: int = 5

    # Database (SQLite default for zero-config; switch to PostgreSQL for production)
    postgres_dsn: str = "sqlite+aiosqlite:///./backend_dev.db"

    # Redis (optional; falls back to in-memory cache)
    redis_url: str = ""
    redis_perm_ttl: int = 60
    redis_model_ttl: int = 300
    redis_rate_window: int = 60

    # Snowflake
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_role: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema: str = ""

    # Rate Limiting
    max_requests_per_minute: int = 60
    max_prompt_length: int = 50000

    # CORS
    cors_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])

    # Model Adapter
    model_adapter_type: str = "litellm"
    allow_mock_adapter: bool = False
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Data bootstrap / seeding
    enable_bootstrap_seed: bool = False


def load_settings() -> Settings:
    cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

    # Keep both common local dev origins enabled even when env var is customized.
    for default_origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        if default_origin not in cors_origins:
            cors_origins.append(default_origin)

    return Settings(
        app_env=os.getenv("APP_ENV", "development").strip().lower(),
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=_to_int("APP_PORT", 8000),
        app_log_level=os.getenv("APP_LOG_LEVEL", "INFO"),
        debug=_to_bool("DEBUG", False),
        jwt_secret=os.getenv("JWT_SECRET", "").strip(),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_hours=_to_int("JWT_EXPIRE_HOURS", 24),
        governance_backend_url=os.getenv("GOVERNANCE_BACKEND_URL", "http://localhost:8000").strip(),
        apps_api_auth_proxy_enabled=_to_bool("APPS_API_AUTH_PROXY_ENABLED", True),
        apps_api_auth_routes_enabled=_to_bool("APPS_API_AUTH_ROUTES_ENABLED", True),
        governance_auth_timeout_seconds=_to_int("GOVERNANCE_AUTH_TIMEOUT_SECONDS", 5),
        postgres_dsn=os.getenv("POSTGRES_DSN", "sqlite+aiosqlite:///./backend_dev.db"),
        redis_url=os.getenv("REDIS_URL", ""),
        redis_perm_ttl=_to_int("REDIS_PERM_TTL", 60),
        redis_model_ttl=_to_int("REDIS_MODEL_TTL", 300),
        redis_rate_window=_to_int("REDIS_RATE_WINDOW", 60),
        snowflake_account=os.getenv("SNOWFLAKE_ACCOUNT", "").strip(),
        snowflake_user=os.getenv("SNOWFLAKE_USER", "").strip(),
        snowflake_password=os.getenv("SNOWFLAKE_PASSWORD", "").strip(),
        snowflake_role=os.getenv("SNOWFLAKE_ROLE", "").strip(),
        snowflake_warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "").strip(),
        snowflake_database=os.getenv("SNOWFLAKE_DATABASE", "").strip(),
        snowflake_schema=os.getenv("SNOWFLAKE_SCHEMA", "").strip(),
        max_requests_per_minute=_to_int("MAX_REQUESTS_PER_MINUTE", 60),
        max_prompt_length=_to_int("MAX_PROMPT_LENGTH", 50000),
        cors_origins=cors_origins,
        model_adapter_type=os.getenv("MODEL_ADAPTER_TYPE", "litellm"),
        allow_mock_adapter=_to_bool("ALLOW_MOCK_ADAPTER", False),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        enable_bootstrap_seed=_to_bool("ENABLE_BOOTSTRAP_SEED", False),
    )
