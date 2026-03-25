# RBAC EXECUTION PLAN — Layer 5
## Complete Step-by-Step Deployment & Testing Guide

---

## STEP 1: CREATE ROLES IN SNOWFLAKE

**File:** `backend/sql/rbac_snowflake_ddl.sql` — Sections 1–2

```sql
-- Run as ORG_ADMIN or SYSADMIN
CREATE ROLE IF NOT EXISTS ORG_ADMIN;
CREATE ROLE IF NOT EXISTS SECURITY_ADMIN;
CREATE ROLE IF NOT EXISTS DATA_ENGINEER;
CREATE ROLE IF NOT EXISTS ANALYTICS_ENGINEER;
CREATE ROLE IF NOT EXISTS DATA_SCIENTIST;
CREATE ROLE IF NOT EXISTS BUSINESS_USER;
CREATE ROLE IF NOT EXISTS VIEWER;
CREATE ROLE IF NOT EXISTS SYSTEM_AGENT;
```

**Verify:** `SHOW ROLES;`

---

## STEP 2: APPLY HIERARCHY GRANTS

**File:** `backend/sql/rbac_snowflake_ddl.sql` — Section 2

```sql
GRANT ROLE ORG_ADMIN          TO ROLE SYSADMIN;
GRANT ROLE SECURITY_ADMIN     TO ROLE ORG_ADMIN;
GRANT ROLE DATA_ENGINEER      TO ROLE ORG_ADMIN;
GRANT ROLE ANALYTICS_ENGINEER TO ROLE DATA_ENGINEER;
GRANT ROLE DATA_SCIENTIST     TO ROLE ANALYTICS_ENGINEER;
GRANT ROLE BUSINESS_USER      TO ROLE DATA_SCIENTIST;
GRANT ROLE VIEWER             TO ROLE BUSINESS_USER;
GRANT ROLE SYSTEM_AGENT       TO ROLE ORG_ADMIN;
```

**Verify:** `SHOW GRANTS TO ROLE ORG_ADMIN;`

---

## STEP 3: ASSIGN PERMISSIONS

**File:** `backend/sql/rbac_snowflake_ddl.sql` — Sections 3–8

Execute in order:
1. Section 3: Warehouse grants (COMPUTE_WH, TRANSFORM_WH)
2. Section 4: Database grants (RAW_DB, STAGING_DB, CURATED_DB, SANDBOX_DB, PUBLISHED_DB, GOVERNANCE_DB)
3. Section 5: Future grants (auto-apply to new objects)
4. Section 6: Secure views access
5. Section 7: Dynamic data masking policies (PII)
6. Section 8: Row access policies

**Verify per role:**
```sql
SHOW GRANTS TO ROLE DATA_ENGINEER;
SHOW GRANTS TO ROLE ANALYTICS_ENGINEER;
SHOW GRANTS TO ROLE SYSTEM_AGENT;
```

---

## STEP 4: MAP USERS TO ROLES

**File:** `backend/sql/rbac_snowflake_ddl.sql` — Section 9

```sql
GRANT ROLE ORG_ADMIN          TO USER <org_admin_user>;
GRANT ROLE SECURITY_ADMIN     TO USER <security_admin_user>;
GRANT ROLE DATA_ENGINEER      TO USER <data_engineer_user>;
GRANT ROLE ANALYTICS_ENGINEER TO USER <analytics_user>;
GRANT ROLE DATA_SCIENTIST     TO USER <scientist_user>;
GRANT ROLE BUSINESS_USER      TO USER <business_user>;
GRANT ROLE VIEWER             TO USER <viewer_user>;
GRANT ROLE SYSTEM_AGENT       TO USER <agent_service_account>;
```

**Verify:** `SHOW GRANTS TO USER <username>;`

---

## STEP 5: INTEGRATE BACKEND RBAC

### 5a. Middleware Registration
Updated `backend/main.py` to use `RBACAuthMiddleware` instead of legacy `JWTAuthMiddleware`.

### 5b. New Files Created
| File | Purpose |
|---|---|
| `backend/core/rbac.py` | Role definitions, permission matrix, hierarchy, agent scopes |
| `backend/middleware/rbac_middleware.py` | Enhanced JWT + RBAC middleware, decorators |
| `backend/services/rbac_service.py` | RBAC service for role management, permission queries |
| `backend/routers/rbac_admin.py` | Admin endpoints for RBAC management |
| `backend/sql/rbac_snowflake_ddl.sql` | Complete Snowflake RBAC SQL script |

### 5c. Updated Files
| File | Changes |
|---|---|
| `backend/models/domain.py` | Added `roles` list to `AuthUser`, `has_role()`, `has_any_role()` |
| `backend/services/snowflake_service.py` | Multi-role Snowflake query (`get_user_all_roles`) |
| `backend/services/auth_service.py` | Multi-role JWT token generation |
| `backend/main.py` | RBAC middleware swap, RBAC router registration, 8-role seed data |
| `backend/routers/admin.py` | Updated `_require_admin` for multi-role check |

### 5d. JWT Token Structure (Updated)
```json
{
  "sub": "user_id_123",
  "email": "analyst@company.com",
  "role": "ANALYTICS_ENGINEER",
  "roles": ["ANALYTICS_ENGINEER", "DATA_SCIENTIST"],
  "display_name": "Jane Doe",
  "iat": 1710000000,
  "exp": 1710003600
}
```

---

## STEP 6: TEST ACCESS SCENARIOS

### API Testing

| # | Test Case | Actor | Action | Expected |
|---|---|---|---|---|
| T1 | Data Engineer reads RAW | `engineer@platform.local` | `GET /skills` | ✅ 200 |
| T2 | Business User blocks pipeline | `business@platform.local` | `POST /pipeline/execute` | ❌ 403 |
| T3 | Viewer reads dashboards | `viewer@platform.local` | `GET /dashboards/view` | ✅ 200 |
| T4 | Data Scientist sees masked PII | `scientist@platform.local` | SELECT email from CURATED | 🔒 Masked |
| T5 | ORG_ADMIN sees unmasked PII | `admin@platform.local` | SELECT email from CURATED | ✅ Unmasked |
| T6 | SYSTEM_AGENT blocked from STAGING | `agent@platform.local` | Access STAGING_DB | ❌ Denied |
| T7 | Business User blocked from admin | `business@platform.local` | `GET /admin/subscriptions` | ❌ 403 |
| T8 | Analytics Engineer uses analytics | `analytics@platform.local` | `GET /analytics/report` | ✅ 200 |
| T9 | ORG_ADMIN full access | `admin@platform.local` | `GET /admin/overview` | ✅ 200 |
| T10 | SECURITY_ADMIN audit access | `security@platform.local` | `GET /rbac/audit/role-changes` | ✅ 200 |

### Backend API Testing (cURL)

```bash
# Login as each role and test access
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@platform.local","password":"admin123"}' | jq -r .access_token)

# Test admin access
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/admin/overview

# Test RBAC endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/rbac/roles
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/rbac/roles/hierarchy
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/rbac/users
```

### Snowflake Testing

```sql
-- Test as DATA_ENGINEER role
USE ROLE DATA_ENGINEER;
SELECT * FROM RAW_DB.PUBLIC.RAW_TABLE LIMIT 1;      -- Should work
SELECT * FROM PUBLISHED_DB.PUBLIC.VIEWS LIMIT 1;     -- Should fail

-- Test as BUSINESS_USER role
USE ROLE BUSINESS_USER;
SELECT * FROM CURATED_DB.PUBLIC.CUSTOMER_VIEW LIMIT 1; -- Should work (masked PII)
INSERT INTO CURATED_DB.PUBLIC.CUSTOMERS VALUES (...);   -- Should fail

-- Test as SYSTEM_AGENT
USE ROLE SYSTEM_AGENT;
SELECT * FROM RAW_DB.INGEST.EVENTS LIMIT 1;          -- Should work
SELECT * FROM STAGING_DB.TRANSFORM.CLEANSED LIMIT 1;  -- Should fail
```

---

## STEP 7: AUDIT AND LOGGING SETUP

### 7a. Enable Query Audit
```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE SECURITY_ADMIN;
```

### 7b. Audit Queries
```sql
-- Who accessed what data
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
WHERE QUERY_START_TIME > DATEADD(day, -7, CURRENT_TIMESTAMP());

-- Query history by role
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE ROLE_NAME = 'DATA_ENGINEER'
ORDER BY START_TIME DESC LIMIT 100;

-- RBAC change audit
SELECT * FROM GOVERNANCE_DB.AUDIT.RBAC_AUDIT_LOG
ORDER BY performed_at DESC LIMIT 50;
```

### 7c. Backend Audit
All API requests are logged via `AuditMiddleware` to the `audit_log` table with:
- user_id, action, outcome, latency, IP, user_agent
- RBAC-specific: role assignments, permission changes

---

## ROLLBACK STRATEGY

```sql
-- Emergency: Revoke all grants for a specific role
REVOKE ALL PRIVILEGES ON DATABASE RAW_DB       FROM ROLE DATA_ENGINEER;
REVOKE ALL PRIVILEGES ON DATABASE STAGING_DB   FROM ROLE DATA_ENGINEER;
REVOKE USAGE ON WAREHOUSE COMPUTE_WH           FROM ROLE DATA_ENGINEER;
REVOKE USAGE ON WAREHOUSE TRANSFORM_WH         FROM ROLE DATA_ENGINEER;

-- Drop a role (must revoke from users first)
REVOKE ROLE DATA_ENGINEER FROM USER <username>;
DROP ROLE IF EXISTS DATA_ENGINEER;

-- Full rollback: drop all custom roles
DROP ROLE IF EXISTS VIEWER;
DROP ROLE IF EXISTS BUSINESS_USER;
DROP ROLE IF EXISTS DATA_SCIENTIST;
DROP ROLE IF EXISTS ANALYTICS_ENGINEER;
DROP ROLE IF EXISTS DATA_ENGINEER;
DROP ROLE IF EXISTS SYSTEM_AGENT;
DROP ROLE IF EXISTS SECURITY_ADMIN;
DROP ROLE IF EXISTS ORG_ADMIN;
```

**Backend rollback:** Revert `main.py` middleware from `RBACAuthMiddleware` back to `JWTAuthMiddleware`.

---

## SECURITY BEST PRACTICES (ENFORCED)

1. **No SYSADMIN inheritance for application roles** — only ORG_ADMIN inherits from SYSADMIN
2. **SYSTEM_AGENT uses dedicated service account** with IP allowlisting
3. **All PII columns have masking policies** — unmasked only for ORG_ADMIN, SECURITY_ADMIN
4. **Row-level access** via ROW ACCESS POLICY on CURATED tables
5. **Future grants** ensure new objects auto-inherit permissions
6. **Separate warehouses** per workload (COMPUTE_WH vs TRANSFORM_WH)
7. **Audit logging** at both Snowflake and backend levels
8. **Token-based auth** with multi-role JWT, 24-hour expiry
9. **Agent scope validation** prevents cross-schema access
10. **Least privilege** — each role gets minimum required permissions
