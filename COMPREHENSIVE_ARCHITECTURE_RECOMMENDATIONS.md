# Comprehensive Architecture Recommendations

## Executive Summary

This document consolidates all architectural findings, security vulnerabilities, and remediation plans for the π-Optimized platform. Based on a thorough analysis, I've identified **12 critical issues** across security, maintainability, scalability, and operational concerns. This document provides a prioritized roadmap for addressing these issues.

**Key Update:** All data storage will be consolidated into Snowflake, eliminating external database dependencies and leveraging Snowflake's cloud data warehouse capabilities for both application data and analytics workloads.

---

## Key Findings Summary

### Critical Issues (P0 - Fix Immediately)

| Issue | Severity | Impact | Status |
|-------|----------|--------|--------|
| Hardcoded JWT Secret | Critical | Authentication bypass | Documented |
| Hardcoded Default Passwords | Critical | Unauthorized access | Documented |
| In-Memory Token Storage | High | Session loss, no revocation | Documented |
| Duplicate MCP Servers | High | Maintenance nightmare | Documented |

### High Priority Issues (P1 - Fix Within 1 Week)

| Issue | Severity | Impact | Status |
|-------|----------|--------|--------|
| No Token Revocation | High | Cannot invalidate compromised tokens | Documented |
| SQLite for Production | Medium | No concurrency, no scaling | Documented |
| No Database Migration Strategy | Medium | Deployment failures | Documented |
| Mixed Service Responsibilities | Medium | Tight coupling | Documented |

### Medium Priority Issues (P2 - Fix Within 1 Month)

| Issue | Severity | Impact | Status |
|-------|----------|--------|--------|
| Weak Password Hashing | Medium | Vulnerable to brute-force | Documented |
| CORS All Methods | Medium | Potential CSRF attacks | Documented |
| No Request Size Limits | Medium | Denial of service risk | Documented |
| No Health Dependencies | Low | False positive health status | Documented |

---

## Deliverables Created

### 1. Architecture Audit Report
**File:** [`ARCHITECTURE_AUDIT_REPORT.md`](ARCHITECTURE_AUDIT_REPORT.md)

**Contents:**
- Executive summary of all findings
- Detailed security vulnerability analysis
- Risk matrix with severity and likelihood
- Immediate action items (P0, P1, P2)
- Short-term, medium-term, and long-term recommendations

**Key Highlights:**
- 12 critical architectural flaws identified
- 5 security vulnerabilities rated Critical/High
- Risk matrix with prioritization
- Clear remediation timeline

---

### 2. MCP Server Consolidation Plan
**File:** [`MCP_SERVER_CONSOLIDATION_PLAN.md`](MCP_SERVER_CONSOLIDATION_PLAN.md)

**Contents:**
- Problem statement and current state analysis
- Feature comparison between implementations
- Recommended approach (consolidate to `server/main.py`)
- 5-phase migration plan with timeline
- Risk mitigation strategies
- Success criteria

**Key Highlights:**
- Two duplicate implementations identified
- Clear consolidation strategy
- 5-week migration timeline
- Rollback plan documented

---

### 3. Authentication & Token Management Strategy
**File:** [`AUTHENTICATION_TOKEN_MANAGEMENT_STRATEGY.md`](AUTHENTICATION_TOKEN_MANAGEMENT_STRATEGY.md)

**Contents:**
- Current state analysis
- Proposed architecture with Redis
- Implementation plan (3 phases)
- Security best practices
- Migration plan with timeline

**Key Highlights:**
- Redis-based token storage
- Token refresh mechanism
- Token revocation capability
- Comprehensive audit logging
- 4-week implementation timeline

---

### 4. Database Migration Plan
**File:** [`DATABASE_MIGRATION_PLAN.md`](DATABASE_MIGRATION_PLAN.md)

**Contents:**
- SQLite limitations analysis
- Snowflake as unified data platform
- Snowflake DDL for all application tables
- Data migration scripts
- Implementation plan (4 phases)
- Rollback plan
- Success criteria

**Key Highlights:**
- SQLite to Snowflake migration
- Single source of truth for all data
- Built-in analytics capabilities
- 4-week migration timeline
- Comprehensive rollback plan

---

### 5. Service Boundaries Architecture
**File:** [`SERVICE_BOUNDARIES_ARCHITECTURE.md`](SERVICE_BOUNDARIES_ARCHITECTURE.md)

**Contents:**
- Current state analysis
- Domain-driven design approach
- Service boundary definitions
- Implementation plan (4 phases)
- Benefits of new architecture

**Key Highlights:**
- 4 clear domains (Auth, Model, Skill, MCP)
- Repository pattern implementation
- Clear separation of concerns
- 4-week migration timeline
- Independent scalability

---

## Implementation Roadmap

### Phase 1: Critical Security Fixes (Week 1)

**Objective:** Address critical security vulnerabilities

**Tasks:**
1. Generate strong JWT secret
2. Remove hardcoded passwords
3. Implement PasswordService with bcrypt
4. Update configuration management

**Deliverables:**
- Secure JWT secret generation
- Random passwords for seeded accounts
- Strong password hashing
- Updated configuration

**Success Criteria:**
- No hardcoded secrets in codebase
- Passwords hashed with bcrypt rounds ≥ 12
- JWT secret is cryptographically secure

---

### Phase 2: Token Management (Week 2)

**Objective:** Implement persistent token storage and revocation

**Tasks:**
1. Set up Redis for token storage
2. Implement TokenService
3. Update authentication middleware
4. Update auth router with refresh/logout

**Deliverables:**
- Redis-based token storage
- Token refresh mechanism
- Token revocation capability
- Session management API

**Success Criteria:**
- 100% token persistence (no in-memory storage)
- Token revocation working within 1 second
- All auth events logged to audit trail

---

### Phase 3: Database Migration (Week 3)

**Objective:** Migrate from SQLite to Snowflake

**Tasks:**
1. Create Snowflake database, schemas, and tables
2. Create data migration scripts
3. Update application configuration
4. Update Snowflake client for application workloads

**Deliverables:**
- Snowflake running and accessible
- All tables created successfully
- All data migrated from SQLite
- Application connects to Snowflake

**Success Criteria:**
- All tests passing
- Query performance acceptable (< 200ms for simple queries)
- No data loss or corruption

---

### Phase 4: Service Boundaries (Week 4)

**Objective:** Implement domain-driven architecture

**Tasks:**
1. Create domain directory structure
2. Implement base classes and interfaces
3. Migrate auth domain
4. Migrate model domain
5. Migrate skill domain

**Deliverables:**
- Clear domain boundaries
- Repository pattern implementation
- Independent domain services
- Updated main application

**Success Criteria:**
- Each domain can be tested in isolation
- Changes localized to specific domains
- Clear interfaces between domains

---

### Phase 5: MCP Server Consolidation (Week 5)

**Objective:** Consolidate duplicate MCP server implementations

**Tasks:**
1. Feature parity audit
2. Port unique features to `server/main.py`
3. Update package scripts
4. Add deprecation notices
5. Remove deprecated implementation

**Deliverables:**
- Single MCP server implementation
- Updated documentation
- Migration guide for users
- Deprecated code removed

**Success Criteria:**
- All features from both implementations available
- All tests passing
- No breaking API changes

---

## Configuration Management Best Practices

### Environment-Specific Configuration

**Development:**
```bash
# .env.local
SNOWFLAKE_ACCOUNT=your_dev_account
SNOWFLAKE_USER=your_dev_user
SNOWFLAKE_PASSWORD=your_dev_password
SNOWFLAKE_ROLE=your_dev_role
SNOWFLAKE_WAREHOUSE=your_dev_warehouse
SNOWFLAKE_DATABASE=pi_optimized
SNOWFLAKE_SCHEMA=app
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-key-change-in-production
DEBUG=true
```

**Staging:**
```bash
# .env.staging
SNOWFLAKE_ACCOUNT=your_staging_account
SNOWFLAKE_USER=your_staging_user
SNOWFLAKE_PASSWORD=${STAGING_SNOWFLAKE_PASSWORD}
SNOWFLAKE_ROLE=your_staging_role
SNOWFLAKE_WAREHOUSE=your_staging_warehouse
SNOWFLAKE_DATABASE=pi_optimized
SNOWFLAKE_SCHEMA=app
REDIS_URL=redis://staging-redis:6379/0
JWT_SECRET=${STAGING_JWT_SECRET}
DEBUG=false
```

**Production:**
```bash
# .env.production (use Docker secrets or Kubernetes secrets)
SNOWFLAKE_ACCOUNT=your_prod_account
SNOWFLAKE_USER=your_prod_user
SNOWFLAKE_PASSWORD=${SNOWFLAKE_PASSWORD}
SNOWFLAKE_ROLE=your_prod_role
SNOWFLAKE_WAREHOUSE=your_prod_warehouse
SNOWFLAKE_DATABASE=pi_optimized
SNOWFLAKE_SCHEMA=app
REDIS_URL=redis://:${REDIS_PASSWORD}@prod-redis:6379/0
JWT_SECRET=${JWT_SECRET}
DEBUG=false
```

### Configuration Validation

**File:** `backend/core/config_validator.py`

```python
"""
Configuration validation utilities.
"""

import os
from typing import Any

from pydantic import BaseModel, validator


class ConfigValidator(BaseModel):
    """Validate configuration settings."""
    
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_role: str
    snowflake_warehouse: str
    snowflake_database: str
    snowflake_schema: str
    redis_url: str
    jwt_secret: str
    debug: bool = False
    
    @validator("snowflake_account")
    def validate_snowflake_account(cls, v):
        """Validate Snowflake account."""
        if not v:
            raise ValueError("SNOWFLAKE_ACCOUNT is required")
        return v
    
    @validator("snowflake_password")
    def validate_snowflake_password(cls, v):
        """Validate Snowflake password."""
        if not v:
            raise ValueError("SNOWFLAKE_PASSWORD is required")
        return v
    
    @validator("redis_url")
    def validate_redis_url(cls, v):
        """Validate Redis URL."""
        if not v:
            raise ValueError("REDIS_URL is required")
        return v
    
    @validator("jwt_secret")
    def validate_jwt_secret(cls, v):
        """Validate JWT secret."""
        if not v:
            raise ValueError("JWT_SECRET is required")
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if v in ["change-me-in-production-please", "secret", "password"]:
            raise ValueError("JWT_SECRET is too weak")
        return v
```

### Secrets Management

**Docker Secrets:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    image: pi-optimized-backend
    secrets:
      - jwt_secret
      - snowflake_password
      - redis_password
    environment:
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
      - SNOWFLAKE_PASSWORD_FILE=/run/secrets/snowflake_password
      - REDIS_PASSWORD_FILE=/run/secrets/redis_password

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  snowflake_password:
    file: ./secrets/snowflake_password.txt
  redis_password:
    file: ./secrets/redis_password.txt
```

**Kubernetes Secrets:**
```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: pi-optimized-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded-secret>
  snowflake-password: <base64-encoded-password>
  redis-password: <base64-encoded-password>
```

---

## Testing Strategy

### Unit Tests

**Coverage Target:** 80%+

**Key Areas:**
- Authentication logic
- Token management
- Password hashing
- Domain services
- Repository implementations

**Example:**
```python
# backend/tests/unit/test_auth_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.domains.auth.services.auth_service import AuthService
from backend.shared.exceptions.domain import ValidationError


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login."""
    # Arrange
    session = AsyncMock()
    settings = MagicMock()
    token_service = AsyncMock()
    
    auth_service = AuthService(session, settings, token_service)
    
    # Act
    result = await auth_service.login(
        email="test@example.com",
        password="password123",
    )
    
    # Assert
    assert "access_token" in result
    assert "refresh_token" in result


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    # Arrange
    session = AsyncMock()
    settings = MagicMock()
    token_service = AsyncMock()
    
    auth_service = AuthService(session, settings, token_service)
    
    # Act & Assert
    with pytest.raises(ValidationError):
        await auth_service.login(
            email="test@example.com",
            password="wrongpassword",
        )
```

### Integration Tests

**Coverage Target:** 70%+

**Key Areas:**
- API endpoints
- Database operations
- Redis operations
- External service integrations

**Example:**
```python
# backend/tests/integration/test_auth_api.py
import pytest
from httpx import AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_login_endpoint():
    """Test login endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@platform.local",
                "password": "admin123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
```

### Security Tests

**Coverage Target:** 100% for critical paths

**Key Areas:**
- Authentication bypass attempts
- Token manipulation
- SQL injection
- XSS attacks
- CSRF attacks

**Example:**
```python
# backend/tests/security/test_auth_security.py
import pytest
from httpx import AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_login_brute_force_protection():
    """Test brute force protection."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Attempt 10 failed logins
        for i in range(10):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": f"wrongpassword{i}",
                },
            )
        
        # 11th attempt should be rate limited
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword11",
            },
        )
        
        assert response.status_code == 429
```

### Performance Tests

**Key Metrics:**
- Response time < 200ms for 95th percentile
- Throughput > 100 requests/second
- Database query time < 50ms
- Redis operation time < 10ms

**Example:**
```python
# backend/tests/performance/test_api_performance.py
import pytest
import asyncio
from httpx import AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_concurrent_logins():
    """Test concurrent login performance."""
    async def login():
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "password123",
                },
            )
            return response.status_code
    
    # Run 100 concurrent logins
    tasks = [login() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    
    # All should succeed
    assert all(r == 200 for r in results)
```

---

## Deployment & Scalability Improvements

### Docker Configuration

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: pi-optimized-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=snowflake://${SNOWFLAKE_USER}:${SNOWFLAKE_PASSWORD}@${SNOWFLAKE_ACCOUNT}/${SNOWFLAKE_DATABASE}/${SNOWFLAKE_SCHEMA}?warehouse=${SNOWFLAKE_WAREHOUSE}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    container_name: pi-optimized-mcp
    ports:
      - "5000:5000"
    environment:
      - SNOWFLAKE_ACCOUNT=${SNOWFLAKE_ACCOUNT}
      - SNOWFLAKE_USER=${SNOWFLAKE_USER}
      - SNOWFLAKE_PASSWORD=${SNOWFLAKE_PASSWORD}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3


  redis:
    image: redis:7-alpine
    container_name: pi-optimized-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  nginx:
    image: nginx:alpine
    container_name: pi-optimized-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - mcp-server

volumes:
  redis_data:
```

### Kubernetes Configuration

**File:** `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pi-optimized-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pi-optimized-backend
  template:
    metadata:
      labels:
        app: pi-optimized-backend
    spec:
      containers:
      - name: backend
        image: pi-optimized-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: SNOWFLAKE_ACCOUNT
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: snowflake-account
        - name: SNOWFLAKE_USER
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: snowflake-user
        - name: SNOWFLAKE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: snowflake-password
        - name: SNOWFLAKE_DATABASE
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: snowflake-database
        - name: SNOWFLAKE_SCHEMA
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: snowflake-schema
        - name: SNOWFLAKE_WAREHOUSE
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: snowflake-warehouse
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: redis-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: pi-optimized-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: pi-optimized-backend
spec:
  selector:
    app: pi-optimized-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### Horizontal Scaling

**Backend Scaling:**
```bash
# Scale backend to 3 replicas
docker-compose up -d --scale backend=3

# Kubernetes scaling
kubectl scale deployment pi-optimized-backend --replicas=3
```

**Database Scaling:**
- Snowflake auto-scaling warehouses
- Query result caching
- Clustering keys for query optimization
- Multi-cluster warehouses for high concurrency

**Redis Scaling:**
- Redis Cluster for high availability
- Redis Sentinel for failover
- Read replicas for read-heavy workloads

---

## Monitoring & Observability

### Health Checks

**Backend Health:**
```python
@app.get("/health")
async def health():
    """Comprehensive health check."""
    checks = {
        "database": await check_database_health(),
        "redis": await check_redis_health(),
        "snowflake": await check_snowflake_health(),
    }
    
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### Metrics

**Key Metrics to Monitor:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Database connection pool usage
- Redis memory usage
- Token generation/revocation rate

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Histogram

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

# Auth metrics
TOKEN_GENERATIONS = Counter(
    "auth_tokens_generated_total",
    "Total tokens generated"
)

TOKEN_REVOCATIONS = Counter(
    "auth_tokens_revoked_total",
    "Total tokens revoked"
)
```

### Logging

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "user_login",
    user_id=user.id,
    email=user.email,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
)
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana Loki
- Datadog

---

## Success Metrics

### Security Metrics
- [ ] Zero hardcoded secrets in codebase
- [ ] 100% token persistence (no in-memory storage)
- [ ] Token revocation working within 1 second
- [ ] Password hashing with bcrypt rounds ≥ 12
- [ ] All auth events logged to audit trail
- [ ] Zero security incidents related to authentication

### Performance Metrics
- [ ] Response time < 200ms for 95th percentile
- [ ] Throughput > 100 requests/second
- [ ] Snowflake query time < 200ms (with caching < 50ms)
- [ ] Redis operation time < 10ms
- [ ] Zero downtime deployments

### Operational Metrics
- [ ] 99.9% uptime
- [ ] Mean time to recovery (MTTR) < 15 minutes
- [ ] Zero data loss incidents
- [ ] All tests passing (unit, integration, security)
- [ ] Documentation up to date

---

## Timeline Summary

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Critical Security Fixes | Secure JWT, password hashing, configuration |
| 2 | Token Management | Redis storage, refresh, revocation |
| 3 | Database Migration | Snowflake migration, data migration |
| 4 | Service Boundaries | Domain architecture, clear boundaries |
| 5 | MCP Consolidation | Single implementation, deprecation |

---

## Next Steps

1. **Review this document** with development team
2. **Prioritize fixes** based on risk matrix
3. **Create remediation tickets** in project management system
4. **Schedule security review** after P0 fixes
5. **Establish regular audit cadence** (quarterly)

---

## Appendix: File Inventory

### Documents Created
1. [`ARCHITECTURE_AUDIT_REPORT.md`](ARCHITECTURE_AUDIT_REPORT.md) - Comprehensive audit findings
2. [`MCP_SERVER_CONSOLIDATION_PLAN.md`](MCP_SERVER_CONSOLIDATION_PLAN.md) - MCP server consolidation plan
3. [`AUTHENTICATION_TOKEN_MANAGEMENT_STRATEGY.md`](AUTHENTICATION_TOKEN_MANAGEMENT_STRATEGY.md) - Auth & token strategy
4. [`DATABASE_MIGRATION_PLAN.md`](DATABASE_MIGRATION_PLAN.md) - Database migration plan
5. [`SERVICE_BOUNDARIES_ARCHITECTURE.md`](SERVICE_BOUNDARIES_ARCHITECTURE.md) - Service boundaries design
6. [`COMPREHENSIVE_ARCHITECTURE_RECOMMENDATIONS.md`](COMPREHENSIVE_ARCHITECTURE_RECOMMENDATIONS.md) - This document

### Key Files to Modify
- `backend/core/config.py` - Configuration management
- `backend/main.py` - Main application
- `backend/services/auth_service.py` - Authentication service
- `backend/middleware/auth.py` - Authentication middleware
- `server/main.py` - MCP server (consolidated)
- `package.json` - NPM scripts

### New Files to Create
- `backend/domains/` - Domain directory structure
- `backend/shared/` - Shared services and utilities
- `backend/migrations/` - Alembic migrations
- `backend/scripts/` - Migration and utility scripts
- `docker-compose.yml` - Docker configuration
- `k8s/` - Kubernetes configuration

---

**Document Version:** 1.0  
**Created:** 2026-03-29  
**Author:** AI Solution Architect  
**Status:** Final - Ready for Review  
**Classification:** Internal - Confidential
