from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.v2.config.settings import Settings
from backend.v2.database.client import RefreshTokenModel, UserModel
from backend.v2.shared.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from backend.v2.shared.logger import get_logger
from backend.v2.shared.utils import generate_id

logger = get_logger("services.auth")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hash.encode("utf-8"))


def create_access_token(user_id: str, org_id: str, email: str, name: str, role: str, roles: list[str], secret: str, algorithm: str, expire_minutes: int) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=expire_minutes)
    return jwt.encode({"sub": user_id, "org_id": org_id, "email": email, "name": name, "role": role, "roles": roles, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}, secret, algorithm=algorithm)


def create_refresh_token_pair(user_id: str, secret: str, algorithm: str, expire_days: int) -> tuple[str, str]:
    raw_token = str(uuid4())
    token_hash = bcrypt.hashpw(raw_token.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    return raw_token, token_hash


class AuthService:
    def __init__(self, settings: Settings, db: AsyncSession):
        self.settings = settings
        self.db = db

    async def login(self, email: str, password: str) -> dict:
        result = await self.db.execute(select(UserModel).where(UserModel.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if user.status != "active":
            raise AuthenticationError("Account is deactivated")

        raw_refresh, token_hash = create_refresh_token_pair(user.id, self.settings.jwt_secret, self.settings.jwt_algorithm, self.settings.jwt_refresh_expire_days)
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_expire_days)
        refresh_record = RefreshTokenModel(id=str(uuid4()), user_id=user.id, token_hash=token_hash, expires_at=expires_at, revoked=False)
        self.db.add(refresh_record)

        access_token = create_access_token(user.id, user.org_id, user.email, user.name, user.role, [user.role], self.settings.jwt_secret, self.settings.jwt_algorithm, self.settings.jwt_access_expire_minutes)

        user.last_active = datetime.now(UTC)
        await self.db.flush()

        return {"access_token": access_token, "refresh_token": raw_refresh, "token_type": "Bearer", "expires_in": self.settings.jwt_access_expire_minutes * 60, "user": {"user_id": user.id, "org_id": user.org_id, "email": user.email, "name": user.name, "role": user.role, "status": user.status}}

    async def refresh(self, refresh_token: str) -> dict:
        result = await self.db.execute(select(RefreshTokenModel).where(RefreshTokenModel.revoked == False))
        tokens = result.scalars().all()
        matched = None
        for t in tokens:
            if bcrypt.checkpw(refresh_token.encode("utf-8"), t.token_hash.encode("utf-8")):
                matched = t
                break
        if not matched:
            raise AuthenticationError("Invalid refresh token")
        if matched.expires_at < datetime.now(UTC):
            matched.revoked = True
            await self.db.flush()
            raise AuthenticationError("Refresh token expired")

        user_result = await self.db.execute(select(UserModel).where(UserModel.id == matched.user_id))
        user = user_result.scalar_one_or_none()
        if not user or user.status != "active":
            raise AuthenticationError("User not found or deactivated")

        matched.revoked = True
        await self.db.flush()

        raw_refresh, new_token_hash = create_refresh_token_pair(user.id, self.settings.jwt_secret, self.settings.jwt_algorithm, self.settings.jwt_refresh_expire_days)
        new_expires_at = datetime.now(UTC) + timedelta(days=self.settings.jwt_refresh_expire_days)
        new_record = RefreshTokenModel(id=str(uuid4()), user_id=user.id, token_hash=new_token_hash, expires_at=new_expires_at, revoked=False)
        self.db.add(new_record)

        access_token = create_access_token(user.id, user.org_id, user.email, user.name, user.role, [user.role], self.settings.jwt_secret, self.settings.jwt_algorithm, self.settings.jwt_access_expire_minutes)
        return {"access_token": access_token, "refresh_token": raw_refresh, "expires_in": self.settings.jwt_access_expire_minutes * 60}

    async def logout(self, refresh_token: str) -> None:
        result = await self.db.execute(select(RefreshTokenModel).where(RefreshTokenModel.revoked == False))
        tokens = result.scalars().all()
        for t in tokens:
            if bcrypt.checkpw(refresh_token.encode("utf-8"), t.token_hash.encode("utf-8")):
                t.revoked = True
                await self.db.flush()
                return

    async def forgot_password(self, email: str) -> None:
        result = await self.db.execute(select(UserModel).where(UserModel.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            return
        logger.info("Password reset requested for %s", email)

    async def reset_password(self, token: str, password: str) -> None:
        raise NotImplementedError("Password reset token validation not yet implemented")

    async def get_me(self, user_id: str) -> dict:
        result = await self.db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")
        return {"user_id": user.id, "org_id": user.org_id, "email": user.email, "name": user.name, "role": user.role, "roles": [user.role], "status": user.status, "last_active": user.last_active.isoformat() if user.last_active else None, "created_at": user.created_at.isoformat() if user.created_at else ""}
