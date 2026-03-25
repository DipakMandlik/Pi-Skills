from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt
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

        # Fetch roles from Snowflake or fall back to stored role
        stored_role = user.platform_role.upper() if user.platform_role else "VIEWER"
        roles: list[str] = [stored_role]

        if self.snowflake.is_configured():
            # Use external_id (Snowflake username) for role lookup, not email
            sf_username = user.external_id or email
            sf_roles = await self.snowflake.get_user_all_roles(sf_username)
            if sf_roles and sf_roles != ["VIEWER"]:
                roles = [r.upper() for r in sf_roles]
                primary_role = roles[0]
                if stored_role != primary_role:
                    await db.execute(
                        update(UserModel)
                        .where(UserModel.id == user.id)
                        .values(platform_role=primary_role)
                    )
                    await cache_delete(f"perm:{user.id}")
                    await db.commit()
                    await db.refresh(user)
                    logger.info("Roles updated from Snowflake for %s (sf_user=%s): %s -> %s", email, sf_username, stored_role, roles)
            else:
                logger.info("Snowflake returned VIEWER for %s (sf_user=%s), keeping stored role: %s", email, sf_username, stored_role)
        else:
            logger.info("Snowflake not configured, using stored role for %s: %s", email, stored_role)

        primary_role = roles[0]

        await db.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(last_login_at=datetime.now(UTC))
        )
        await db.commit()

        now = datetime.now(UTC)
        exp = now + timedelta(hours=self.settings.jwt_expire_hours)

        token = jwt.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": primary_role,
                "roles": roles,
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
            "role": primary_role,
            "roles": roles,
            "user_id": str(user.id),
            "display_name": user.display_name or "",
        }

    async def get_me(self, user: AuthUser, db: AsyncSession) -> dict:
        from ..core.rbac import get_role_permissions
        from ..services.permission_service import resolve_user_permissions

        perms = await resolve_user_permissions(user.user_id, db)
        role_perms = get_role_permissions(user.role)

        return {
            "user_id": user.user_id,
            "email": user.email,
            "role": user.role,
            "roles": user.roles,
            "display_name": user.display_name,
            "allowed_models": perms.allowed_models,
            "allowed_skills": perms.allowed_skills,
            "rbac_permissions": {
                "snowflake_permissions": role_perms.get("snowflake_permissions", []),
                "api_permissions": role_perms.get("api_permissions", []),
                "environment_scope": role_perms.get("environment_scope", []),
                "inherited_roles": role_perms.get("inherited_roles", []),
            },
            "token_expires_at": datetime.fromtimestamp(
                user.token_exp, tz=UTC
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
