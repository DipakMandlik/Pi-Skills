# Authentication & Token Management Strategy

## Executive Summary

This document outlines a comprehensive authentication and token management strategy to address critical security vulnerabilities identified in the π-Optimized platform. The strategy focuses on secure credential management, persistent token storage, token revocation capabilities, and defense-in-depth security practices.

---

## Current State Analysis

### Critical Issues Identified

1. **Hardcoded JWT Secret** - Default value "change-me-in-production-please"
2. **In-Memory Token Storage** - Tokens lost on restart, no persistence
3. **No Token Revocation** - Cannot invalidate compromised tokens
4. **Weak Password Hashing** - No bcrypt work factor specified
5. **Hardcoded Default Passwords** - Predictable credentials for seeded accounts

### Current Authentication Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Backend   │────▶│  Snowflake  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   SQLite    │
                    │   (Users)   │
                    └─────────────┘
```

**Issues:**
- No centralized token management
- No token persistence
- No revocation mechanism
- No audit trail for token operations

---

## Proposed Architecture

### High-Level Design

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Backend   │────▶│  Snowflake  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │◀── Token Store
                    │  (Tokens)   │◀── Session Cache
                    └─────────────┘◀── Rate Limiting
                           │
                           ▼
                    ┌─────────────┐
                    │ PostgreSQL  │◀── User Data
                    │   (Audit)   │◀── Audit Logs
                    └─────────────┘
```

### Components

1. **JWT Token Service** - Centralized token generation and validation
2. **Redis Token Store** - Persistent token storage with TTL
3. **Token Revocation Service** - Blacklist/whitelist management
4. **Audit Service** - Comprehensive logging of auth events
5. **Password Service** - Secure password hashing and validation

---

## Implementation Plan

### Phase 1: Secure Credential Management (Week 1)

#### 1.1 Generate Strong JWT Secret

**File:** `backend/core/config.py`

```python
import secrets
import os
from pathlib import Path

def generate_jwt_secret() -> str:
    """Generate a cryptographically secure JWT secret."""
    return secrets.token_urlsafe(64)

def load_jwt_secret() -> str:
    """Load JWT secret from environment or generate one."""
    secret = os.getenv("JWT_SECRET")
    
    if not secret:
        # Check for secret file (Docker secrets, Kubernetes secrets)
        secret_file = Path("/run/secrets/jwt_secret")
        if secret_file.exists():
            return secret_file.read_text().strip()
        
        # Generate and save to .env.local for development
        secret = generate_jwt_secret()
        env_local = Path(".env.local")
        if env_local.exists():
            with open(env_local, "a") as f:
                f.write(f"\nJWT_SECRET={secret}\n")
        
        logger.warning("JWT_SECRET not set. Generated temporary secret.")
    
    return secret
```

**Configuration:**
```python
@dataclass(frozen=True)
class Settings:
    jwt_secret: str = field(default_factory=load_jwt_secret)
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 1  # Reduced from 24 to 1 hour
    jwt_refresh_expire_days: int = 7  # New: refresh token expiration
```

#### 1.2 Remove Hardcoded Passwords

**File:** `backend/main.py`

```python
async def _seed_data():
    # ... existing code ...
    
    # Generate random passwords for seeded accounts
    import secrets
    import string
    
    def generate_password(length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits + string.punctuation
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Store generated passwords in secure location
    generated_passwords = {}
    
    seed_users = [
        UserModel(
            id=admin_id,
            external_id="PIQLENS",
            email="admin@platform.local",
            display_name="Platform Admin",
            platform_role="ORG_ADMIN",
            password_hash=pw_hash(generate_password())
        ),
        # ... other users ...
    ]
    
    # Save generated passwords to secure file (for initial setup only)
    passwords_file = Path(".generated_passwords.json")
    if not passwords_file.exists():
        import json
        with open(passwords_file, "w") as f:
            json.dump(generated_passwords, f, indent=2)
        logger.info("Generated passwords saved to .generated_passwords.json")
```

#### 1.3 Strengthen Password Hashing

**File:** `backend/services/auth_service.py`

```python
import bcrypt

class PasswordService:
    """Secure password hashing service."""
    
    # OWASP recommended: 2^12 = 4096 iterations
    BCRYPT_ROUNDS = 12
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt and random salt."""
        salt = bcrypt.gensalt(rounds=PasswordService.BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8")
            )
        except Exception:
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password meets security requirements."""
        if len(password) < 12:
            return False, "Password must be at least 12 characters"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain digit"
        
        if not any(c in string.punctuation for c in password):
            return False, "Password must contain special character"
        
        return True, "Password meets requirements"
```

---

### Phase 2: Persistent Token Storage (Week 2)

#### 2.1 Redis Token Store

**File:** `backend/services/token_service.py`

```python
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger("backend.token_service")


class TokenData(BaseModel):
    """Token data structure."""
    token_id: str
    user_id: str
    email: str
    role: str
    roles: list[str]
    created_at: datetime
    expires_at: datetime
    refresh_token_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class TokenService:
    """Centralized token management service."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.access_token_ttl = timedelta(hours=1)
        self.refresh_token_ttl = timedelta(days=7)
    
    async def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str,
        roles: list[str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Create access and refresh tokens.
        
        Returns:
            Tuple of (access_token, refresh_token)
        """
        import jwt
        from ..core.config import load_settings
        
        settings = load_settings()
        now = datetime.utcnow()
        
        # Generate unique token IDs
        access_token_id = str(uuid4())
        refresh_token_id = str(uuid4())
        
        # Create access token payload
        access_payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "roles": roles,
            "jti": access_token_id,  # JWT ID for revocation
            "iat": int(now.timestamp()),
            "exp": int((now + self.access_token_ttl).timestamp()),
            "type": "access",
        }
        
        # Create refresh token payload
        refresh_payload = {
            "sub": user_id,
            "jti": refresh_token_id,
            "iat": int(now.timestamp()),
            "exp": int((now + self.refresh_token_ttl).timestamp()),
            "type": "refresh",
        }
        
        # Encode tokens
        access_token = jwt.encode(
            access_payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        
        refresh_token = jwt.encode(
            refresh_payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        
        # Store token data in Redis
        access_token_data = TokenData(
            token_id=access_token_id,
            user_id=user_id,
            email=email,
            role=role,
            roles=roles,
            created_at=now,
            expires_at=now + self.access_token_ttl,
            refresh_token_id=refresh_token_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        refresh_token_data = {
            "token_id": refresh_token_id,
            "user_id": user_id,
            "access_token_id": access_token_id,
            "created_at": now.isoformat(),
            "expires_at": (now + self.refresh_token_ttl).isoformat(),
        }
        
        # Store in Redis with TTL
        await self.redis.setex(
            f"token:access:{access_token_id}",
            int(self.access_token_ttl.total_seconds()),
            access_token_data.json(),
        )
        
        await self.redis.setex(
            f"token:refresh:{refresh_token_id}",
            int(self.refresh_token_ttl.total_seconds()),
            json.dumps(refresh_token_data),
        )
        
        # Track user's active tokens
        await self.redis.sadd(f"user:tokens:{user_id}", access_token_id)
        await self.redis.expire(f"user:tokens:{user_id}", int(self.refresh_token_ttl.total_seconds()))
        
        logger.info(
            "Tokens created for user %s (access=%s, refresh=%s)",
            user_id,
            access_token_id,
            refresh_token_id,
        )
        
        return access_token, refresh_token
    
    async def validate_access_token(self, token: str) -> Optional[TokenData]:
        """
        Validate access token and return token data.
        
        Returns:
            TokenData if valid, None if invalid or revoked
        """
        import jwt
        from ..core.config import load_settings
        
        settings = load_settings()
        
        try:
            # Decode token
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            
            # Check token type
            if payload.get("type") != "access":
                return None
            
            token_id = payload.get("jti")
            if not token_id:
                return None
            
            # Check if token is revoked
            is_revoked = await self.redis.exists(f"token:revoked:{token_id}")
            if is_revoked:
                logger.warning("Revoked token used: %s", token_id)
                return None
            
            # Get token data from Redis
            token_data_json = await self.redis.get(f"token:access:{token_id}")
            if not token_data_json:
                logger.warning("Token not found in store: %s", token_id)
                return None
            
            return TokenData.parse_raw(token_data_json)
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token: %s", e)
            return None
    
    async def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[tuple[str, str]]:
        """
        Refresh access token using refresh token.
        
        Returns:
            Tuple of (new_access_token, new_refresh_token) if valid, None otherwise
        """
        import jwt
        from ..core.config import load_settings
        
        settings = load_settings()
        
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            
            # Check token type
            if payload.get("type") != "refresh":
                return None
            
            refresh_token_id = payload.get("jti")
            user_id = payload.get("sub")
            
            if not refresh_token_id or not user_id:
                return None
            
            # Check if refresh token exists
            refresh_data_json = await self.redis.get(f"token:refresh:{refresh_token_id}")
            if not refresh_data_json:
                logger.warning("Refresh token not found: %s", refresh_token_id)
                return None
            
            refresh_data = json.loads(refresh_data_json)
            
            # Revoke old access token
            old_access_token_id = refresh_data.get("access_token_id")
            if old_access_token_id:
                await self.revoke_token(old_access_token_id)
            
            # Get user data from database
            from ..core.database import get_session, UserModel
            from sqlalchemy import select
            
            async with get_session() as db:
                result = await db.execute(
                    select(UserModel).where(UserModel.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.is_active:
                    return None
                
                # Create new tokens
                new_access_token, new_refresh_token = await self.create_access_token(
                    user_id=user.id,
                    email=user.email,
                    role=user.platform_role,
                    roles=[user.platform_role],
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                
                # Revoke old refresh token
                await self.redis.delete(f"token:refresh:{refresh_token_id}")
                
                return new_access_token, new_refresh_token
                
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid refresh token: %s", e)
            return None
    
    async def revoke_token(self, token_id: str) -> None:
        """Revoke a specific token."""
        # Add to revoked tokens set with TTL
        await self.redis.setex(
            f"token:revoked:{token_id}",
            int(self.refresh_token_ttl.total_seconds()),
            "1",
        )
        
        # Remove from active tokens
        await self.redis.delete(f"token:access:{token_id}")
        
        logger.info("Token revoked: %s", token_id)
    
    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a user.
        
        Returns:
            Number of tokens revoked
        """
        # Get all user's active tokens
        token_ids = await self.redis.smembers(f"user:tokens:{user_id}")
        
        revoked_count = 0
        for token_id in token_ids:
            await self.revoke_token(token_id.decode())
            revoked_count += 1
        
        # Clear user's token set
        await self.redis.delete(f"user:tokens:{user_id}")
        
        logger.info("Revoked %d tokens for user %s", revoked_count, user_id)
        return revoked_count
    
    async def get_user_active_tokens(self, user_id: str) -> list[TokenData]:
        """Get all active tokens for a user."""
        token_ids = await self.redis.smembers(f"user:tokens:{user_id}")
        
        active_tokens = []
        for token_id in token_ids:
            token_data_json = await self.redis.get(f"token:access:{token_id.decode()}")
            if token_data_json:
                active_tokens.append(TokenData.parse_raw(token_data_json))
        
        return active_tokens
```

#### 2.2 Update Authentication Middleware

**File:** `backend/middleware/auth.py`

```python
from __future__ import annotations

import logging
from typing import Optional

import jwt
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from ..core.config import Settings
from ..core.redis_client import get_redis
from ..models.domain import AuthUser
from ..services.token_service import TokenService

logger = logging.getLogger("backend.auth_middleware")

PUBLIC_PATHS = {"/auth/login", "/auth/refresh", "/health", "/docs", "/openapi.json", "/redoc"}


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.token_service = TokenService(get_redis())

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _error_response(401, "Unauthorized", "Missing or invalid authorization header")

        token = auth_header[7:]
        
        # Validate token using TokenService
        token_data = await self.token_service.validate_access_token(token)
        
        if not token_data:
            return _error_response(401, "Unauthorized", "Invalid or expired token")

        request_id = getattr(request.state, "request_id", "")
        request.state.user = AuthUser(
            user_id=token_data.user_id,
            email=token_data.email,
            role=token_data.role,
            roles=token_data.roles,
            request_id=request_id,
            token_exp=int(token_data.expires_at.timestamp()),
        )

        return await call_next(request)


def _error_response(status: int, title: str, detail: str) -> Response:
    import json
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=status,
        content={"status": status, "title": title, "detail": detail},
    )
```

#### 2.3 Update Auth Router

**File:** `backend/routers/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..core.redis_client import get_redis
from ..models.domain import AuthUser
from ..schemas.api import LoginRequest, LoginResponse, RefreshRequest
from ..services.auth_service import AuthService, AuthError
from ..services.token_service import TokenService
from ..services.snowflake_service import SnowflakeService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_session),
):
    """Authenticate user and return tokens."""
    try:
        auth_service = AuthService(settings, SnowflakeService(settings))
        token_service = TokenService(get_redis())
        
        # Authenticate user
        user_data = await auth_service.login(body.email, body.password, db)
        
        # Create tokens
        access_token, refresh_token = await token_service.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            role=user_data["role"],
            roles=user_data["roles"],
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.jwt_expire_hours * 3600,
            user_id=user_data["user_id"],
            role=user_data["role"],
            roles=user_data["roles"],
        )
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    request: Request,
    body: RefreshRequest,
):
    """Refresh access token using refresh token."""
    token_service = TokenService(get_redis())
    
    result = await token_service.refresh_access_token(
        refresh_token=body.refresh_token,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    access_token, refresh_token = result
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.jwt_expire_hours * 3600,
    )


@router.post("/logout")
async def logout(
    current_user: AuthUser = Depends(get_current_user),
):
    """Revoke current user's tokens."""
    token_service = TokenService(get_redis())
    revoked_count = await token_service.revoke_all_user_tokens(current_user.user_id)
    
    return {"message": f"Logged out successfully. Revoked {revoked_count} tokens."}


@router.get("/sessions")
async def list_sessions(
    current_user: AuthUser = Depends(get_current_user),
):
    """List all active sessions for current user."""
    token_service = TokenService(get_redis())
    active_tokens = await token_service.get_user_active_tokens(current_user.user_id)
    
    return {
        "sessions": [
            {
                "token_id": token.token_id,
                "created_at": token.created_at.isoformat(),
                "expires_at": token.expires_at.isoformat(),
                "ip_address": token.ip_address,
                "user_agent": token.user_agent,
            }
            for token in active_tokens
        ]
    }


@router.delete("/sessions/{token_id}")
async def revoke_session(
    token_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Revoke a specific session."""
    token_service = TokenService(get_redis())
    
    # Verify token belongs to user
    active_tokens = await token_service.get_user_active_tokens(current_user.user_id)
    token_ids = [t.token_id for t in active_tokens]
    
    if token_id not in token_ids:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await token_service.revoke_token(token_id)
    
    return {"message": "Session revoked successfully"}
```

---

### Phase 3: Audit Logging (Week 3)

#### 3.1 Enhanced Audit Service

**File:** `backend/services/audit_service.py`

```python
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AuditLogModel

logger = logging.getLogger("backend.audit_service")


class AuditService:
    """Comprehensive audit logging service."""
    
    async def log_auth_event(
        self,
        db: AsyncSession,
        event_type: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_detail: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Log authentication event."""
        audit_log = AuditLogModel(
            id=str(uuid4()),
            request_id=str(uuid4()),
            user_id=user_id,
            action=f"auth.{event_type}",
            outcome="SUCCESS" if success else "FAILURE",
            ip_address=ip_address,
            user_agent=user_agent,
            error_detail=error_detail,
            metadata_={
                "email": email,
                "event_type": event_type,
                **(metadata or {}),
            },
            timestamp=datetime.utcnow(),
        )
        
        db.add(audit_log)
        await db.commit()
        
        logger.info(
            "Auth event: %s user=%s email=%s success=%s ip=%s",
            event_type,
            user_id,
            email,
            success,
            ip_address,
        )
    
    async def log_token_event(
        self,
        db: AsyncSession,
        event_type: str,
        token_id: str,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Log token-related event."""
        audit_log = AuditLogModel(
            id=str(uuid4()),
            request_id=str(uuid4()),
            user_id=user_id,
            action=f"token.{event_type}",
            outcome="SUCCESS",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_={
                "token_id": token_id,
                "event_type": event_type,
                **(metadata or {}),
            },
            timestamp=datetime.utcnow(),
        )
        
        db.add(audit_log)
        await db.commit()
        
        logger.info(
            "Token event: %s token=%s user=%s ip=%s",
            event_type,
            token_id,
            user_id,
            ip_address,
        )
```

---

## Security Best Practices

### 1. Token Storage
- **Never store tokens in localStorage** - Vulnerable to XSS
- **Use httpOnly cookies** for refresh tokens
- **Use sessionStorage** for access tokens (cleared on tab close)
- **Implement token rotation** on refresh

### 2. Token Expiration
- **Access tokens:** 15-60 minutes (short-lived)
- **Refresh tokens:** 7-30 days (long-lived)
- **Implement sliding window** for active users

### 3. Token Revocation
- **Blacklist approach** - Store revoked token IDs
- **Whitelist approach** - Store only valid token IDs (more secure)
- **Implement token versioning** - Increment version on password change

### 4. Password Security
- **Minimum 12 characters**
- **Require complexity** (upper, lower, digit, special)
- **Check against breached passwords** (HaveIBeenPwned API)
- **Implement password history** (prevent reuse of last 5 passwords)

### 5. Rate Limiting
- **Login attempts:** 5 per minute per IP
- **Token refresh:** 10 per minute per user
- **API calls:** 60 per minute per user

---

## Migration Plan

### Week 1: Foundation
- [ ] Generate strong JWT secret
- [ ] Remove hardcoded passwords
- [ ] Implement PasswordService
- [ ] Update configuration

### Week 2: Token Management
- [ ] Set up Redis for token storage
- [ ] Implement TokenService
- [ ] Update authentication middleware
- [ ] Update auth router

### Week 3: Audit & Monitoring
- [ ] Enhance AuditService
- [ ] Add auth event logging
- [ ] Set up monitoring dashboards
- [ ] Implement alerting

### Week 4: Testing & Rollout
- [ ] Comprehensive security testing
- [ ] Penetration testing
- [ ] Gradual rollout (canary deployment)
- [ ] Monitor for issues

---

## Success Metrics

- [ ] Zero hardcoded secrets in codebase
- [ ] 100% token persistence (no in-memory storage)
- [ ] Token revocation working within 1 second
- [ ] Password hashing with bcrypt rounds ≥ 12
- [ ] All auth events logged to audit trail
- [ ] Rate limiting preventing brute-force attacks
- [ ] Zero security incidents related to authentication

---

**Document Version:** 1.0  
**Created:** 2026-03-29  
**Author:** AI Solution Architect  
**Status:** Draft - Pending Review
