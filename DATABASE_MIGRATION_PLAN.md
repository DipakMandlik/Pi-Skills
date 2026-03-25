# Database Migration Plan: Security-Aligned Snowflake Cutover

## Executive Summary

This plan migrates persistent platform data to Snowflake without regressing the security hardening already implemented in backend and MCP services.

Primary goal:
- Make Snowflake the authoritative operational store for core governance data.

Non-negotiable constraints:
- Keep strict JWT secret startup validation in place.
- Keep persistent, revocable session chains in place.
- Keep negative auth tests and security harness green before and after cutover.

---

## Current Baseline (Must Be Preserved)

The platform now includes these security controls and behaviors:
- Strict JWT secret validation at startup (missing, weak, or placeholder values fail fast).
- Persistent session storage with access/refresh token rotation and revocation chains.
- Explicit logout and chain-wide invalidation semantics.
- Negative tests for invalid token, expired token, weak/missing secret, refresh reuse attacks.
- Full security harness expectations aligned to blocked status codes.

Migration work must not remove or bypass any of these controls.

---

## Scope

In scope:
- Snowflake schemas and tables for operational governance data.
- Data migration from current operational store to Snowflake.
- Repository/service-level backend changes to point at Snowflake.
- Validation and staged cutover with rollback.

Out of scope for this document:
- Replacing opaque session tokens with JWT sessions.
- Relaxing current auth/rate/role policies.
- UI redesign or unrelated feature development.

---

## Target Snowflake Layout

Database:
- `PI_OPTIMIZED`

Schemas:
- `APP` for operational tables
- `AUDIT` for audit trail and monitoring records
- `ANALYTICS` for derived reporting views

Warehouses:
- `PI_APP_WH` for application workloads
- `PI_ANALYTICS_WH` for reporting workloads

Notes:
- Snowflake does not support traditional inline `INDEX` DDL syntax used by PostgreSQL/MySQL.
- Use clustering, search optimization service, and query design instead of inline indexes.

---

## Canonical Security-Sensitive Tables

The following entities are mandatory for parity with current behavior:

Core identity and access:
- `users`
- `model_permissions`
- `skill_assignments`
- `registered_models`
- `model_access_control`
- `feature_flags`

Subscription and quotas:
- `subscriptions`
- `user_subscriptions`
- `user_tokens`
- `token_usage_log`
- `cost_tracking`

Security and audit:
- `audit_log`
- `mcp_sessions` (persistent, revocable session store)

`mcp_sessions` minimum fields:
- `session_id`
- `user_id`
- `access_token_hash`
- `refresh_token_hash`
- `parent_session_id` (for rotation chain)
- `is_revoked`
- `revoked_at`
- `expires_at`
- `created_at`
- `updated_at`

Important:
- Store token hashes, not raw tokens.
- Enforce uniqueness on token hashes.
- Support chain-wide revocation queries efficiently.

---

## Implementation Phases

## Phase 1: Foundation and DDL

Deliverables:
- Snowflake warehouse/database/schema creation scripts.
- Production-ready DDL for all operational tables, including `mcp_sessions`.
- Role grants and least-privilege access for app service accounts.

Acceptance criteria:
- DDL applies cleanly in non-prod.
- No unsupported SQL patterns (for example inline `INDEX`).
- Session table supports revoke-by-chain operations.

## Phase 2: Repository/Service Migration

Deliverables:
- Keep current service interfaces stable.
- Replace storage adapters/repositories to read/write Snowflake.
- Preserve middleware behavior, token verification, and revocation semantics.

Implementation rule:
- Do not replace stable auth code paths with broad rewrites.
- Migrate data-access boundaries first, keep route/service contracts unchanged.

Acceptance criteria:
- Existing auth and governance flows behave identically through API contracts.
- Startup validation and secret rules unchanged.

## Phase 3: Data Migration and Backfill

Deliverables:
- Idempotent migration scripts.
- Batch migration with resumability and row-count checks.
- Data reconciliation report by table.

Migration order (dependency-safe):
1. `users`
2. `registered_models`
3. `subscriptions`
4. `user_subscriptions`
5. `model_access_control`
6. `feature_flags`
7. `model_permissions`
8. `skill_assignments`
9. `user_tokens`
10. `token_usage_log`
11. `cost_tracking`
12. `audit_log`
13. `mcp_sessions`

Acceptance criteria:
- Row counts and key integrity checks pass.
- No orphaned foreign references.
- Session chains remain valid for active sessions.

## Phase 4: Security Regression Gate

Mandatory pre-cutover gate:
- All targeted auth/security tests pass.
- Full security harness passes (all attacks blocked per policy).

Required command set:
- `py -3.12 -m pytest apps/mcp/tests/test_server_main_security.py`
- `py -3.12 -m pytest apps/api/tests/test_auth_negative.py`
- `npm run test:security`

Acceptance criteria:
- 0 failing tests in above suites.
- No newly introduced auth bypass paths.

## Phase 5: Staged Cutover

Rollout approach:
- Non-prod canary first.
- Production cutover during defined window.
- Enhanced observability for auth failures, refresh failures, and revocation checks.

Acceptance criteria:
- Health endpoints stable.
- Auth/login/refresh/logout SLOs within threshold.
- No spike in token validation failures beyond expected baseline.

---

## Validation Checklist

Functional:
- Login succeeds with valid credentials.
- Invalid/expired tokens are rejected.
- Weak/missing JWT secret blocks startup.
- Refresh rotation revokes reused or superseded chains.
- Logout revokes entire active chain.

Data integrity:
- Row count parity per migrated table.
- Key uniqueness and not-null constraints validated.
- Session hash uniqueness and chain references validated.

Performance:
- P95 for key auth endpoints remains acceptable.
- No sustained increase in error rate.

---

## Rollback Plan

Rollback triggers:
- Security test failure after cutover.
- Elevated auth error rates or session integrity failures.
- Data corruption or irreconcilable mismatch.

Rollback actions:
1. Switch application writes back to previous operational store.
2. Keep Snowflake snapshot for forensic comparison.
3. Re-run security regression suite on rolled-back state.
4. Open incident review and root-cause remediation before retry.

---

## Deliverables by File

Planned files to update/create during implementation:
- `backend/sql/snowflake_ddl.sql`
- `backend/scripts/migrate_to_snowflake.py`
- `backend/core/config.py` (Snowflake settings only; keep security checks intact)
- data-access repositories under `backend/services/` and/or `backend/core/`
- migration validation report under `results/`

---

## Go/No-Go Criteria

Go only if all are true:
- Security regression gate fully green.
- Data reconciliation complete with signed review.
- Rollback tested and documented.
- Monitoring dashboards and alerts active for auth/session paths.

Otherwise:
- No production cutover.

---

Document Version: 3.0
Created: 2026-03-29
Updated: 2026-03-29
Status: Implementation In Progress