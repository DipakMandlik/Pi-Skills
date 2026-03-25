# Service Boundaries & Separation of Concerns

## Executive Summary

This document defines clear service boundaries and separation of concerns for the π-Optimized platform. The current architecture suffers from mixed responsibilities, tight coupling, and unclear boundaries between components. This document proposes a microservices-inspired architecture with well-defined domains and interfaces.

---

## Current State Analysis

### Identified Issues

1. **Mixed Responsibilities**
   - Backend contains both API and MCP server code
   - Services handle multiple unrelated concerns
   - No clear domain boundaries

2. **Tight Coupling**
   - Direct database access from multiple services
   - Shared models across different domains
   - No clear dependency injection

3. **Unclear Boundaries**
   - MCP server duplicated in two locations
   - Authentication logic scattered across files
   - No clear API versioning strategy

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Backend                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │  Auth   │  │ Models  │  │ Skills  │  │Execute  │      │
│  │ Router  │  │ Router  │  │ Router  │  │ Router  │      │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │
│       │            │            │            │              │
│       └────────────┴────────────┴────────────┘              │
│                          │                                  │
│                    ┌─────┴─────┐                           │
│                    │ Services  │                           │
│                    └───────────┘                           │
│                          │                                  │
│                    ┌─────┴─────┐                           │
│                    │ Database  │                           │
│                    └───────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

**Problems:**
- All routers share same database connection
- Services are tightly coupled
- No clear domain boundaries
- Difficult to scale independently

---

## Proposed Architecture

### Domain-Driven Design (DDD) Approach

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│                    (FastAPI Router)                         │
└─────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Auth Domain   │ │  Model Domain   │ │  Skill Domain   │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ • Authentication│ │ • Model Registry│ │ • Skill Registry│
│ • Authorization │ │ • Access Control│ │ • Assignments   │
│ • Token Mgmt    │ │ • Permissions   │ │ • Execution     │
│ • User Mgmt     │ │ • Subscriptions │ │ • Monitoring    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                    ┌──────┴──────┐
                    │  Shared     │
                    │  Services   │
                    └─────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   PostgreSQL    │ │     Redis       │ │   Snowflake     │
│   (Users,       │ │   (Tokens,      │ │   (Data         │
│    Models,      │ │    Cache,       │ │    Warehouse)   │
│    Skills)      │ │    Sessions)    │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Service Boundaries

### 1. Authentication Domain

**Responsibilities:**
- User authentication (login/logout)
- Token generation and validation
- Session management
- Password management
- User registration

**Components:**
```
backend/domains/auth/
├── __init__.py
├── routers/
│   ├── __init__.py
│   ├── auth.py          # Login, logout, refresh
│   └── users.py         # User management
├── services/
│   ├── __init__.py
│   ├── auth_service.py  # Authentication logic
│   ├── token_service.py # Token management
│   └── password_service.py # Password hashing
├── models/
│   ├── __init__.py
│   └── domain.py        # Auth domain models
└── schemas/
    ├── __init__.py
    └── api.py           # API request/response schemas
```

**API Endpoints:**
```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
POST   /api/v1/auth/register
PUT    /api/v1/auth/password
GET    /api/v1/auth/sessions
DELETE /api/v1/auth/sessions/{id}
```

**Dependencies:**
- PostgreSQL (user data)
- Redis (token storage)
- Snowflake (role synchronization)

---

### 2. Model Domain

**Responsibilities:**
- AI model registry
- Model access control
- Permission management
- Subscription management
- Cost tracking

**Components:**
```
backend/domains/model/
├── __init__.py
├── routers/
│   ├── __init__.py
│   ├── models.py        # Model registry
│   ├── permissions.py   # Model permissions
│   └── subscriptions.py # Subscription management
├── services/
│   ├── __init__.py
│   ├── model_service.py      # Model CRUD
│   ├── permission_service.py # Permission management
│   ├── subscription_service.py # Subscription logic
│   └── cost_service.py       # Cost tracking
├── models/
│   ├── __init__.py
│   └── domain.py        # Model domain models
└── schemas/
    ├── __init__.py
    └── api.py           # API request/response schemas
```

**API Endpoints:**
```
# Models
GET    /api/v1/models
GET    /api/v1/models/{id}
POST   /api/v1/models
PUT    /api/v1/models/{id}
DELETE /api/v1/models/{id}

# Permissions
GET    /api/v1/models/{id}/permissions
POST   /api/v1/models/{id}/permissions
DELETE /api/v1/models/{id}/permissions/{user_id}

# Subscriptions
GET    /api/v1/subscriptions
GET    /api/v1/subscriptions/{name}
POST   /api/v1/subscriptions
PUT    /api/v1/subscriptions/{name}
DELETE /api/v1/subscriptions/{name}

# User Subscriptions
GET    /api/v1/users/{id}/subscription
POST   /api/v1/users/{id}/subscription
DELETE /api/v1/users/{id}/subscription
```

**Dependencies:**
- PostgreSQL (model data)
- Redis (permission cache)

---

### 3. Skill Domain

**Responsibilities:**
- Skill registry
- Skill assignments
- Skill execution
- Execution monitoring

**Components:**
```
backend/domains/skill/
├── __init__.py
├── routers/
│   ├── __init__.py
│   ├── skills.py        # Skill registry
│   └── execute.py       # Skill execution
├── services/
│   ├── __init__.py
│   ├── skill_service.py      # Skill CRUD
│   ├── assignment_service.py # Skill assignments
│   └── execution_service.py  # Skill execution
├── models/
│   ├── __init__.py
│   └── domain.py        # Skill domain models
└── schemas/
    ├── __init__.py
    └── api.py           # API request/response schemas
```

**API Endpoints:**
```
# Skills
GET    /api/v1/skills
GET    /api/v1/skills/{id}
POST   /api/v1/skills
PUT    /api/v1/skills/{id}
DELETE /api/v1/skills/{id}

# Assignments
GET    /api/v1/users/{id}/skills
POST   /api/v1/users/{id}/skills
DELETE /api/v1/users/{id}/skills/{skill_id}

# Execution
POST   /api/v1/execute
GET    /api/v1/execute/{id}
GET    /api/v1/execute/{id}/status
```

**Dependencies:**
- PostgreSQL (skill data)
- Snowflake (skill execution)

---

### 4. MCP Server (Separate Service)

**Responsibilities:**
- Snowflake tool registry
- Tool execution
- Tool discovery
- SSE event streaming

**Components:**
```
server/
├── __init__.py
├── main.py              # FastAPI application
├── config.py            # Configuration
├── security.py          # Security utilities
├── snowflake_client.py  # Snowflake client
├── tool_registry.py     # Tool registry
└── requirements.txt     # Dependencies
```

**API Endpoints:**
```
GET    /health
POST   /auth/login
POST   /auth/refresh
GET    /users/me
GET    /mcp/tools
POST   /mcp/call
GET    /mcp/events
```

**Dependencies:**
- Snowflake (data warehouse)
- Redis (token storage)

---

### 5. Shared Services

**Responsibilities:**
- Audit logging
- Monitoring
- Configuration management
- Common utilities

**Components:**
```
backend/shared/
├── __init__.py
├── services/
│   ├── __init__.py
│   ├── audit_service.py    # Audit logging
│   ├── monitoring_service.py # Monitoring
│   └── cache_service.py    # Caching
├── utils/
│   ├── __init__.py
│   ├── validators.py       # Input validation
│   ├── formatters.py       # Data formatting
│   └── helpers.py          # Common helpers
└── exceptions/
    ├── __init__.py
    └── domain.py           # Domain exceptions
```

---

## Implementation Plan

### Phase 1: Create Domain Structure (Week 1)

#### 1.1 Create Domain Directories

```bash
mkdir -p backend/domains/{auth,model,skill}/routers
mkdir -p backend/domains/{auth,model,skill}/services
mkdir -p backend/domains/{auth,model,skill}/models
mkdir -p backend/domains/{auth,model,skill}/schemas
mkdir -p backend/shared/{services,utils,exceptions}
```

#### 1.2 Create Domain Base Classes

**File:** `backend/domains/base.py`

```python
"""
Base classes for domain-driven design.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository for data access."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @abstractmethod
    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_all(self, **filters) -> list[T]:
        """Get all entities with optional filters."""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        pass


class BaseService(ABC):
    """Base service for business logic."""
    
    def __init__(self, repository: BaseRepository):
        self.repository = repository


class BaseRouter(ABC):
    """Base router for API endpoints."""
    
    def __init__(self, service: BaseService):
        self.service = service
```

#### 1.3 Create Domain Exceptions

**File:** `backend/shared/exceptions/domain.py`

```python
"""
Domain-specific exceptions.
"""


class DomainError(Exception):
    """Base domain exception."""
    pass


class NotFoundError(DomainError):
    """Entity not found."""
    pass


class ValidationError(DomainError):
    """Validation error."""
    pass


class AuthorizationError(DomainError):
    """Authorization error."""
    pass


class ConflictError(DomainError):
    """Conflict error (e.g., duplicate entry)."""
    pass


class BusinessRuleError(DomainError):
    """Business rule violation."""
    pass
```

---

### Phase 2: Migrate Auth Domain (Week 2)

#### 2.1 Create Auth Repository

**File:** `backend/domains/auth/repositories/user_repository.py`

```python
"""
User repository for data access.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domains.base import BaseRepository
from backend.core.database import UserModel


class UserRepository(BaseRepository[UserModel]):
    """User repository."""
    
    async def get_by_id(self, id: str) -> Optional[UserModel]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, **filters) -> list[UserModel]:
        """Get all users with optional filters."""
        query = select(UserModel)
        
        if "is_active" in filters:
            query = query.where(UserModel.is_active == filters["is_active"])
        
        if "platform_role" in filters:
            query = query.where(UserModel.platform_role == filters["platform_role"])
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, user: UserModel) -> UserModel:
        """Create new user."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update(self, user: UserModel) -> UserModel:
        """Update existing user."""
        await self.session.merge(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete(self, id: str) -> bool:
        """Delete user by ID."""
        user = await self.get_by_id(id)
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False
```

#### 2.2 Create Auth Service

**File:** `backend/domains/auth/services/auth_service.py`

```python
"""
Authentication service.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings
from backend.domains.auth.repositories.user_repository import UserRepository
from backend.domains.auth.services.token_service import TokenService
from backend.shared.exceptions.domain import NotFoundError, ValidationError

logger = logging.getLogger("backend.auth_service")


class AuthService:
    """Authentication service."""
    
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        token_service: TokenService,
    ):
        self.session = session
        self.settings = settings
        self.token_service = token_service
        self.user_repository = UserRepository(session)
    
    async def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict with access_token, refresh_token, and user info
            
        Raises:
            ValidationError: If credentials are invalid
        """
        # Get user by email
        user = await self.user_repository.get_by_email(email)
        
        if not user:
            logger.warning("Login attempt for non-existent user: %s", email)
            raise ValidationError("Invalid credentials")
        
        if not user.is_active:
            logger.warning("Login attempt for inactive user: %s", email)
            raise ValidationError("Account is disabled")
        
        # Verify password
        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            logger.warning("Invalid password for user: %s", email)
            raise ValidationError("Invalid credentials")
        
        # Create tokens
        access_token, refresh_token = await self.token_service.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.platform_role,
            roles=[user.platform_role],
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.user_repository.update(user)
        
        logger.info("User logged in: %s", email)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.settings.jwt_expire_hours * 3600,
            "user_id": user.id,
            "email": user.email,
            "role": user.platform_role,
            "roles": [user.platform_role],
        }
    
    async def logout(self, user_id: str) -> int:
        """
        Logout user by revoking all tokens.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        revoked_count = await self.token_service.revoke_all_user_tokens(user_id)
        logger.info("User logged out: %s (revoked %d tokens)", user_id, revoked_count)
        return revoked_count
    
    async def get_current_user(self, user_id: str) -> dict:
        """
        Get current user information.
        
        Args:
            user_id: User ID
            
        Returns:
            User information dict
            
        Raises:
            NotFoundError: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        
        if not user:
            raise NotFoundError(f"User not found: {user_id}")
        
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.platform_role,
            "roles": [user.platform_role],
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
```

#### 2.3 Create Auth Router

**File:** `backend/domains/auth/routers/auth.py`

```python
"""
Authentication router.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_session
from backend.core.redis_client import get_redis
from backend.domains.auth.schemas.api import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserResponse,
)
from backend.domains.auth.services.auth_service import AuthService
from backend.domains.auth.services.token_service import TokenService
from backend.shared.exceptions.domain import NotFoundError, ValidationError

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    """Get auth service instance."""
    from backend.core.config import load_settings
    settings = load_settings()
    token_service = TokenService(get_redis())
    return AuthService(session, settings, token_service)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return tokens."""
    try:
        return await auth_service.login(
            email=body.email,
            password=body.password,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
        )
    except ValidationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout user by revoking all tokens."""
    user_id = request.state.user.user_id
    revoked_count = await auth_service.logout(user_id)
    return {"message": f"Logged out successfully. Revoked {revoked_count} tokens."}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get current user information."""
    try:
        user_id = request.state.user.user_id
        return await auth_service.get_current_user(user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

---

### Phase 3: Migrate Model Domain (Week 3)

#### 3.1 Create Model Repository

**File:** `backend/domains/model/repositories/model_repository.py`

```python
"""
Model repository for data access.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domains.base import BaseRepository
from backend.core.database import RegisteredModelModel


class ModelRepository(BaseRepository[RegisteredModelModel]):
    """Model repository."""
    
    async def get_by_id(self, id: str) -> Optional[RegisteredModelModel]:
        """Get model by ID."""
        result = await self.session.execute(
            select(RegisteredModelModel).where(RegisteredModelModel.model_id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, **filters) -> list[RegisteredModelModel]:
        """Get all models with optional filters."""
        query = select(RegisteredModelModel)
        
        if "is_available" in filters:
            query = query.where(RegisteredModelModel.is_available == filters["is_available"])
        
        if "provider" in filters:
            query = query.where(RegisteredModelModel.provider == filters["provider"])
        
        if "tier" in filters:
            query = query.where(RegisteredModelModel.tier == filters["tier"])
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, model: RegisteredModelModel) -> RegisteredModelModel:
        """Create new model."""
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model
    
    async def update(self, model: RegisteredModelModel) -> RegisteredModelModel:
        """Update existing model."""
        await self.session.merge(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model
    
    async def delete(self, id: str) -> bool:
        """Delete model by ID."""
        model = await self.get_by_id(id)
        if model:
            await self.session.delete(model)
            await self.session.commit()
            return True
        return False
```

---

### Phase 4: Update Main Application (Week 4)

#### 4.1 Update Main Application

**File:** `backend/main.py`

```python
"""
Main application with domain-based routing.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import load_settings
from backend.core.database import create_tables, init_engine
from backend.core.redis_client import init_redis
from backend.middleware.audit import AuditMiddleware
from backend.middleware.rbac_middleware import RBACAuthMiddleware
from backend.middleware.request_id import RequestIDMiddleware

# Import domain routers
from backend.domains.auth.routers.auth import router as auth_router
from backend.domains.model.routers.models import router as models_router
from backend.domains.skill.routers.skills import router as skills_router

settings = load_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    # Startup
    init_engine(settings)
    init_redis(settings.redis_url)
    await create_tables()
    
    yield
    
    # Shutdown
    pass


app = FastAPI(
    title="AI Governance Platform",
    version="2.0.0",
    description="Policy enforcement engine for AI model access control",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(AuditMiddleware)
app.add_middleware(RBACAuthMiddleware, settings=settings)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include domain routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Health check endpoint."""
    from backend.core.database import check_database_health
    from backend.core.redis_client import _use_redis, get_redis
    
    db_ok = await check_database_health()
    redis_ok = False
    
    if _use_redis:
        try:
            r = get_redis()
            await r.ping()
            redis_ok = True
        except Exception:
            pass
    else:
        redis_ok = True
    
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else ("in-memory" if not _use_redis else "disconnected"),
    }


def run():
    """Run the application."""
    uvicorn.run(
        "backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.app_log_level.lower(),
    )


if __name__ == "__main__":
    run()
```

---

## Benefits of New Architecture

### 1. Clear Separation of Concerns
- Each domain has specific responsibilities
- No overlap between domains
- Easy to understand and maintain

### 2. Independent Scalability
- Each domain can be scaled independently
- Can be extracted to microservices if needed
- Clear boundaries for deployment

### 3. Better Testability
- Each domain can be tested in isolation
- Clear interfaces for mocking
- Easier to write unit tests

### 4. Improved Maintainability
- Changes are localized to specific domains
- Reduced risk of breaking other domains
- Easier to onboard new developers

### 5. Technology Flexibility
- Each domain can use different technologies
- Can optimize for specific use cases
- Easier to adopt new technologies

---

## Migration Checklist

- [ ] Create domain directory structure
- [ ] Create base classes and interfaces
- [ ] Migrate auth domain
- [ ] Migrate model domain
- [ ] Migrate skill domain
- [ ] Update main application
- [ ] Update tests
- [ ] Update documentation
- [ ] Deploy and validate

---

**Document Version:** 1.0  
**Created:** 2026-03-29  
**Author:** AI Solution Architect  
**Status:** Draft - Pending Review
