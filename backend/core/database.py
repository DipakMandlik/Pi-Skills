from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import Settings

logger = logging.getLogger("backend.database")


# ── Portable column types ───────────────────────────────────────────

class GUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return None

    def process_result_value(self, value, dialect):
        return value


class JSONEncoded(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None and isinstance(value, str):
            return json.loads(value)
        return value


class INETType(TypeDecorator):
    impl = String(45)
    cache_ok = True


# ── Base ────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Models ──────────────────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    external_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255))
    platform_role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_login_at = Column(DateTime)
    metadata_ = Column("metadata", JSONEncoded, default=dict)


class ModelPermissionModel(Base):
    __tablename__ = "model_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "model_id", name="uq_user_model"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    model_id = Column(String(255), nullable=False)
    granted_by = Column(GUID(), nullable=False)
    granted_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    revoked_by = Column(GUID())
    revoked_at = Column(DateTime)
    notes = Column(Text)


class SkillAssignmentModel(Base):
    __tablename__ = "skill_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    skill_id = Column(String(255), nullable=False)
    assigned_by = Column(GUID(), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    revoked_by = Column(GUID())
    revoked_at = Column(DateTime)


class SkillDefinitionModel(Base):
    __tablename__ = "skill_definitions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_definition_version"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    skill_id = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    skill_type = Column(String(50), nullable=False, default="ai")
    domain = Column(String(100), nullable=False, default="general")
    instructions = Column(Text, nullable=False, default="")
    required_models = Column(JSONEncoded, default=list)
    input_schema = Column(JSONEncoded, default=dict)
    output_format = Column(JSONEncoded, default=dict)
    execution_handler = Column(String(500), nullable=False)
    error_handling = Column(JSONEncoded, default=dict)
    created_by = Column(GUID(), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(GUID())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SkillStateModel(Base):
    __tablename__ = "skill_states"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_skill_state_version"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    skill_id = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    skill_type = Column(String(50), nullable=False, default="ai")
    domain = Column(String(100), nullable=False, default="general")
    notes = Column(Text)
    updated_by = Column(GUID(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), index=True)


class RegisteredModelModel(Base):
    __tablename__ = "registered_models"

    model_id = Column(String(255), primary_key=True)
    display_name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    tier = Column(String(50), default="standard")
    is_available = Column(Boolean, default=True)
    max_tokens = Column(Integer)
    cost_per_1k_tokens = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())


class SecretReferenceModel(Base):
    __tablename__ = "secret_references"
    __table_args__ = (
        UniqueConstraint("reference_key", name="uq_secret_reference_key"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    reference_key = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    encrypted_payload = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(GUID(), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ModelConfigurationModel(Base):
    __tablename__ = "model_configurations"
    __table_args__ = (
        UniqueConstraint("model_id", "provider", name="uq_model_configuration"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    model_id = Column(String(255), nullable=False, index=True)
    provider = Column(String(100), nullable=False, index=True)
    base_url = Column(String(500), nullable=False)
    secret_reference_key = Column(String(255), nullable=False)
    temperature = Column(Float, nullable=False, default=0.2)
    max_tokens = Column(Integer, nullable=False, default=2048)
    request_timeout_seconds = Column(Integer, nullable=False, default=30)
    parameters = Column(JSONEncoded, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(GUID(), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(GUID())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    request_id = Column(GUID(), nullable=False)
    user_id = Column(GUID(), index=True)
    skill_id = Column(String(255))
    model_id = Column(String(255))
    action = Column(String(100), nullable=False)
    outcome = Column(String(50), nullable=False)
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    ip_address = Column(INETType)
    user_agent = Column(Text)
    error_detail = Column(Text)
    metadata_ = Column("metadata", JSONEncoded, default=dict)
    timestamp = Column(DateTime, server_default=func.now())


# ── Governance Models ───────────────────────────────────────────────

class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    plan_name = Column(String(100), primary_key=True)
    display_name = Column(String(255), nullable=False)
    monthly_token_limit = Column(Integer, nullable=False)
    max_tokens_per_request = Column(Integer, nullable=False, default=4096)
    allowed_models = Column(JSONEncoded, default=list)
    features = Column(JSONEncoded, default=list)
    priority = Column(String(50), nullable=False, default="standard")
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    cost_budget_monthly = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserSubscriptionModel(Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_subscription"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    plan_name = Column(String(100), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())
    assigned_by = Column(GUID())
    is_active = Column(Boolean, default=True)


class UserTokenModel(Base):
    __tablename__ = "user_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_user_period"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    period = Column(String(7), nullable=False)
    tokens_used = Column(Integer, nullable=False, default=0)
    tokens_limit = Column(Integer, nullable=False)
    cost_accumulated = Column(Float, nullable=False, default=0.0)
    last_reset = Column(DateTime, server_default=func.now())


class TokenUsageLogModel(Base):
    __tablename__ = "token_usage_log"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    model_id = Column(String(255), nullable=False, index=True)
    skill_id = Column(String(255))
    tokens_used = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False, default=0.0)
    request_id = Column(GUID())
    latency_ms = Column(Integer)
    outcome = Column(String(50), nullable=False, default="SUCCESS")
    timestamp = Column(DateTime, server_default=func.now())


class ModelAccessControlModel(Base):
    __tablename__ = "model_access_control"

    model_id = Column(String(255), primary_key=True)
    allowed_roles = Column(JSONEncoded, default=list)
    max_tokens_per_request = Column(Integer, nullable=False, default=4096)
    enabled = Column(Boolean, default=True)
    rate_limit_per_minute = Column(Integer, default=60)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FeatureFlagModel(Base):
    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("feature_name", "model_id", name="uq_feature_model"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    feature_name = Column(String(255), nullable=False)
    model_id = Column(String(255), nullable=False)
    enabled_for = Column(JSONEncoded, default=list)
    enabled = Column(Boolean, default=True)
    config = Column(JSONEncoded, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CostTrackingModel(Base):
    __tablename__ = "cost_tracking"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    period = Column(String(7), nullable=False, index=True)
    model_id = Column(String(255), nullable=False)
    tokens_used = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    recorded_at = Column(DateTime, server_default=func.now())


# ── Engine + Session ────────────────────────────────────────────────

_engine = None
_session_factory = None


def _get_dsn(settings: Settings) -> str:
    dsn = settings.postgres_dsn
    if "postgresql" in dsn:
        return dsn.replace("postgresql+asyncpg", "postgresql+asyncpg")
    return dsn


def init_engine(settings: Settings):
    global _engine, _session_factory

    dsn = _get_dsn(settings)

    # Auto-detect: if postgresql DSN but no PostgreSQL available, fallback to SQLite
    if "postgresql" in dsn:
        try:
            # Quick test if asyncpg is usable
            import asyncpg  # noqa: F401
        except Exception:
            logger.warning("asyncpg not available, falling back to SQLite")
            dsn = "sqlite+aiosqlite:///./backend_dev.db"

    logger.info("Database engine: %s", dsn.split("@")[-1] if "@" in dsn else dsn)

    _engine = create_async_engine(
        dsn,
        echo=settings.debug,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database engine not initialised. Call init_engine() first.")
    async with _session_factory() as session:
        yield session


async def create_tables():
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_engine() first.")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
