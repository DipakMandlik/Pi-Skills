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
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    debug: bool = False

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    database_url: str = "sqlite+aiosqlite:///./backend_dev.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    redis_url: str = ""
    redis_perm_ttl: int = 60
    redis_model_ttl: int = 300

    cors_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])

    rate_limit_per_minute: int = 60
    auth_rate_limit_per_15min: int = 5
    max_request_body_bytes: int = 10240
    max_file_upload_bytes: int = 5242880

    enable_bootstrap_seed: bool = False

    environment: str = "development"


def load_settings() -> Settings:
    cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

    for default_origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        if default_origin not in cors_origins:
            cors_origins.append(default_origin)

    return Settings(
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=_to_int("APP_PORT", 8000),
        app_log_level=os.getenv("APP_LOG_LEVEL", "INFO"),
        debug=_to_bool("DEBUG", False),
        jwt_secret=os.getenv("JWT_SECRET", "").strip(),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_access_expire_minutes=_to_int("JWT_ACCESS_EXPIRE_MINUTES", 15),
        jwt_refresh_expire_days=_to_int("JWT_REFRESH_EXPIRE_DAYS", 7),
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./backend_dev.db"),
        database_pool_size=_to_int("DATABASE_POOL_SIZE", 10),
        database_max_overflow=_to_int("DATABASE_MAX_OVERFLOW", 20),
        redis_url=os.getenv("REDIS_URL", ""),
        redis_perm_ttl=_to_int("REDIS_PERM_TTL", 60),
        redis_model_ttl=_to_int("REDIS_MODEL_TTL", 300),
        cors_origins=cors_origins,
        rate_limit_per_minute=_to_int("RATE_LIMIT_PER_MINUTE", 60),
        auth_rate_limit_per_15min=_to_int("AUTH_RATE_LIMIT_PER_15MIN", 5),
        max_request_body_bytes=_to_int("MAX_REQUEST_BODY_BYTES", 10240),
        max_file_upload_bytes=_to_int("MAX_FILE_UPLOAD_BYTES", 5242880),
        enable_bootstrap_seed=_to_bool("ENABLE_BOOTSTRAP_SEED", False),
        environment=os.getenv("ENVIRONMENT", "development"),
    )
