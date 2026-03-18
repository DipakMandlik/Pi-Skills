from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv('.env.local')
load_dotenv('.env')


@dataclass(frozen=True)
class Settings:
    mcp_host: str
    mcp_port: int
    mcp_log_level: str
    mcp_cors_origins: list[str]
    sql_safety_mode: str
    sql_default_row_limit: int
    sql_max_rows: int
    sql_timeout_seconds: int
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_role: str
    snowflake_warehouse: str
    snowflake_database: str
    snowflake_schema: str
    snowflake_log_level: str
    suppress_cloud_metadata_probes: bool


def _to_int(name: str, fallback: int) -> int:
    raw = os.getenv(name, str(fallback)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


def _to_bool(name: str, fallback: bool) -> bool:
    raw = os.getenv(name, str(fallback)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    cors_raw = os.getenv(
        "MCP_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
    )
    cors_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

    return Settings(
        mcp_host=os.getenv("MCP_HOST", "0.0.0.0"),
        mcp_port=_to_int("MCP_PORT", 5000),
        mcp_log_level=os.getenv("MCP_LOG_LEVEL", "INFO"),
        mcp_cors_origins=cors_origins,
        sql_safety_mode=os.getenv("SQL_SAFETY_MODE", "dev").lower(),
        sql_default_row_limit=_to_int("SQL_DEFAULT_ROW_LIMIT", 1000),
        sql_max_rows=_to_int("SQL_MAX_ROWS", 5000),
        sql_timeout_seconds=_to_int("SQL_TIMEOUT_SECONDS", 60),
        snowflake_account=os.getenv("SNOWFLAKE_ACCOUNT", "").strip(),
        snowflake_user=os.getenv("SNOWFLAKE_USER", "").strip(),
        snowflake_password=os.getenv("SNOWFLAKE_PASSWORD", "").strip(),
        snowflake_role=os.getenv("SNOWFLAKE_ROLE", "").strip(),
        snowflake_warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "").strip(),
        snowflake_database=os.getenv("SNOWFLAKE_DATABASE", "").strip(),
        snowflake_schema=os.getenv("SNOWFLAKE_SCHEMA", "").strip(),
        snowflake_log_level=os.getenv("SNOWFLAKE_LOG_LEVEL", "ERROR").strip().upper(),
        suppress_cloud_metadata_probes=_to_bool("SUPPRESS_CLOUD_METADATA_PROBES", True),
    )


def validate_required_env(settings: Settings) -> list[str]:
    missing: list[str] = []
    required = {
        "SNOWFLAKE_ACCOUNT": settings.snowflake_account,
        "SNOWFLAKE_USER": settings.snowflake_user,
        "SNOWFLAKE_PASSWORD": settings.snowflake_password,
        "SNOWFLAKE_ROLE": settings.snowflake_role,
        "SNOWFLAKE_WAREHOUSE": settings.snowflake_warehouse,
        "SNOWFLAKE_DATABASE": settings.snowflake_database,
        "SNOWFLAKE_SCHEMA": settings.snowflake_schema,
    }
    for key, value in required.items():
        if not value:
            missing.append(key)
    return missing
