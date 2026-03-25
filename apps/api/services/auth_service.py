from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import jwt
import bcrypt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings
from ..core.database import UserModel
from ..core.redis_client import cache_delete
from ..models.domain import AuthUser
from ..services.snowflake_service import SnowflakeService

logger = logging.getLogger("backend.auth_service")


class AuthService:
    def __init__(self, settings: Settings, snowflake: SnowflakeService):
        self.settings = settings
        self.snowflake = snowflake

    async def login(self, email: str, password: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(UserModel).where(UserModel.email == email, UserModel.is_active == True)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise AuthError("Invalid credentials")

        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            raise AuthError("Invalid credentials")

        sf_role = await self.snowflake.get_user_platform_role(email)

        if user.platform_role != sf_role:
            await db.execute(
                update(UserModel)
                .where(UserModel.id == user.id)
                .values(platform_role=sf_role)
            )
            await cache_delete(f"perm:{user.id}")
            await db.commit()
            await db.refresh(user)

        await db.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await db.commit()

        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=self.settings.jwt_expire_hours)

        token = jwt.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": sf_role,
                "display_name": user.display_name or "",
                "iat": int(now.timestamp()),
                "exp": int(exp.timestamp()),
            },
            self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
        )

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.settings.jwt_expire_hours * 3600,
            "role": sf_role,
            "user_id": str(user.id),
            "display_name": user.display_name or "",
        }

    async def get_me(self, user: AuthUser, db: AsyncSession) -> dict:
        from ..services.permission_service import resolve_user_permissions

        perms = await resolve_user_permissions(user.user_id, db)

        return {
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role,
            "display_name": user.display_name,
            "allowed_models": perms.allowed_models,
            "allowed_skills": perms.allowed_skills,
            "token_expires_at": datetime.fromtimestamp(
                user.token_exp, tz=timezone.utc
            ).isoformat(),
        }

    async def create_user(
        self,
        email: str,
        password: str,
        display_name: str,
        role: str,
        db: AsyncSession,
    ) -> UserModel:
        existing = await db.execute(select(UserModel).where(UserModel.email == email))
        if existing.scalar_one_or_none() is not None:
            raise AuthError("User already exists")

        user = UserModel(
            id=str(uuid4()),
            external_id=email,
            email=email,
            display_name=display_name,
            platform_role=role,
            password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


class AuthError(Exception):
    pass
