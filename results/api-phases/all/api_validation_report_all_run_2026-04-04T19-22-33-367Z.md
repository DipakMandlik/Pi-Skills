# API Validation Report
**Date:** 2026-04-04 19:22
**Pass Rate:** 100.0% (119/119)

| Test ID | Title | Module | Status | Expected | Actual |
|---------|-------|--------|--------|----------|--------|
| AUTH-001 | AUTH-001 | Auth | ✅ PASS | 200 with access_token and role:ADMIN/ORG_ADMIN | 200 ORG_ADMIN |
| AUTH-003 | AUTH-003 | Auth | ✅ PASS | 401 | 401 |
| AUTH-004 | AUTH-004 | Auth | ✅ PASS | 401 | 401 |
| AUTH-005 | AUTH-005 | Auth | ✅ PASS | 400 or 422 | 422 |
| AUTH-006 | Valid /auth/me | Auth | ✅ PASS | 200 with user_id, email, role | 200 fields:user_id,email,role,roles,display_name,allowed_models,allowed_skills,rbac_permissions,token_expires_at |
| AUTH-007 | AUTH-007 | Auth | ✅ PASS | 401 | 401 |
| AUTH-011 | AUTH-011 | Auth | ✅ PASS | 401 or 422 (not 500) | 401 |
| RBAC-001 | RBAC-001 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-002 | RBAC-002 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-003 | RBAC-003 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-004 | RBAC-004 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-005 | RBAC-005 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-006 | RBAC-006 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-007 | RBAC-007 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-008 | RBAC-008 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-009 | RBAC-009 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-010 | RBAC-010 | RBAC | ✅ PASS | 403 | 403 |
| RBAC-BODY | RBAC-BODY | RBAC | ✅ PASS | 403 | 403 |
| RBAC-HEADER | RBAC-HEADER | RBAC | ✅ PASS | 403 | 403 |
| RBAC-NOTOKEN | RBAC-NOTOKEN | RBAC | ✅ PASS | 401 | 401 |
| EXEC-002 | EXEC-002 | ExecutionGuard | ✅ PASS | 400 or 403 | 403 |
| EXEC-012 | EXEC-012 | ExecutionGuard | ✅ PASS | 401 | 401 |
| EXEC-014-0 | EXEC-014-0 | ExecutionGuard | ✅ PASS | 4xx (not 500) | 422 |
| EXEC-014-1 | EXEC-014-1 | ExecutionGuard | ✅ PASS | 4xx (not 500) | 422 |
| EXEC-014-2 | EXEC-014-2 | ExecutionGuard | ✅ PASS | 4xx (not 500) | 422 |
| EXEC-014-3 | EXEC-014-3 | ExecutionGuard | ✅ PASS | 4xx (not 500) | 422 |
| EXEC-009-0 | EXEC-009-0 | ExecutionGuard | ✅ PASS | 403 | 403 |
| EXEC-009-1 | EXEC-009-1 | ExecutionGuard | ✅ PASS | 403 | 403 |
| EXEC-009-2 | EXEC-009-2 | ExecutionGuard | ✅ PASS | 403 | 403 |
| EXEC-009-3 | EXEC-009-3 | ExecutionGuard | ✅ PASS | 403 | 403 |
| EXEC-009-4 | EXEC-009-4 | ExecutionGuard | ✅ PASS | 403 | 403 |
| EXEC-018 | EXEC-018 | ExecutionGuard | ✅ PASS | 400 or 422 | 422 |
| MOD-016 | MOD-016 | ExecutionGuard | ✅ PASS | 400 or 422 | 422 |
| MOD-017-0 | MOD-017-0 | ExecutionGuard | ✅ PASS | 400 or 422 | 422 |
| MOD-017-1 | MOD-017-1 | ExecutionGuard | ✅ PASS | 400 or 422 | 422 |
| MOD-017-2 | MOD-017-2 | ExecutionGuard | ✅ PASS | 400 or 422 | 422 |
| SEC-001 | SEC-001 | Security | ✅ PASS | 401 | 401 |
| SEC-MALF-0 | SEC-MALF-0 | Security | ✅ PASS | 400 or 401 | 401 |
| SEC-MALF-1 | SEC-MALF-1 | Security | ✅ PASS | 400 or 401 | 401 |
| SEC-MALF-2 | SEC-MALF-2 | Security | ✅ PASS | 400 or 401 | 401 |
| SEC-MALF-3 | SEC-MALF-3 | Security | ✅ PASS | 400 or 401 | 401 |
| SEC-MALF-4 | SEC-MALF-4 | Security | ✅ PASS | 400 or 401 | 401 |
| SEC-MALF-5 | SEC-MALF-5 | Security | ✅ PASS | 400 or 401 | 401 |
| LOG-001 | LOG-001 | Monitoring | ✅ PASS | 200 | 200 |
| LOG-002 | LOG-002 | Monitoring | ✅ PASS | Log entry with DENIED action | Actions: PROMPT_POLICY_VIOLATION,INJECTION_ATTEMPT_DETECTED,PROMPT_POLICY_VIOLATION,INJECTION_ATTEMPT_DETECTED,PROMPT_POLICY_VIOLATION,INJECTION_ATTEMPT_DETECTED,PROMPT_POLICY_VIOLATION,EXEC_FAILED |
| LOG-FIELDS | LOG-FIELDS | Monitoring | ✅ PASS | All fields present | All present |
| MON-RBAC-ADMIN-SCOPE | MON-RBAC-ADMIN-SCOPE | Monitoring | ✅ PASS | 403 | 403 |
| MON-RBAC-SELF-SCOPE | MON-RBAC-SELF-SCOPE | Monitoring | ✅ PASS | 200 with user-scoped logs | 200 count:64 |
| LOG-009 | LOG-009 | Monitoring | ✅ PASS | 401 | 401 |
| ADM-001 | ADM-001 | Admin | ✅ PASS | 200 | 200 |
| ADM-001-RBAC | ADM-001-RBAC | Admin | ✅ PASS | 403 | 403 |
| ADM-002 | ADM-002 | Admin | ✅ PASS | 200 | 200 |
| ADM-002-RBAC | ADM-002-RBAC | Admin | ✅ PASS | 403 | 403 |
| ADM-003 | ADM-003 | Admin | ✅ PASS | 200 | 200 |
| ADM-003-RBAC | ADM-003-RBAC | Admin | ✅ PASS | 403 | 403 |
| ADM-004 | ADM-004 | Admin | ✅ PASS | 200 | 200 |
| ADM-004-RBAC | ADM-004-RBAC | Admin | ✅ PASS | 403 | 403 |
| AI-001 | AI-001 | AI-Intelligence | ✅ PASS | 200 | 200 |
| AI-001-RBAC | AI-001-RBAC | AI-Intelligence | ✅ PASS | 403 | 403 |
| AI-002 | AI-002 | AI-Intelligence | ✅ PASS | 200 | 200 |
| AI-002-RBAC | AI-002-RBAC | AI-Intelligence | ✅ PASS | 403 | 403 |
| AI-003 | AI-003 | AI-Intelligence | ✅ PASS | 200 | 200 |
| AI-003-RBAC | AI-003-RBAC | AI-Intelligence | ✅ PASS | 403 | 403 |
| AI-004 | AI-004 | AI-Intelligence | ✅ PASS | 200 | 200 |
| AI-004-RBAC | AI-004-RBAC | AI-Intelligence | ✅ PASS | 403 | 403 |
| ADM-SUB-001 | ADM-SUB-001 | Admin | ✅ PASS | 200 | 200 |
| ADM-SUB-001-NEG | ADM-SUB-001-NEG | Admin | ✅ PASS | 400 or 422 | 422 |
| ADM-SUB-002 | ADM-SUB-002 | Admin | ✅ PASS | 200 with matching plan_name | 200 test-plan-mnkpyyvc |
| ADM-SUB-002-NEG | ADM-SUB-002-NEG | Admin | ✅ PASS | 404 | 404 |
| ADM-SUB-003 | ADM-SUB-003 | Admin | ✅ PASS | 200 with updated display_name | 200 Plan mnkpyyvc Updated |
| ADM-SUB-004 | ADM-SUB-004 | Admin | ✅ PASS | 200 with user_subscriptions array | 200 |
| ADM-SUB-005-RBAC | ADM-SUB-005-RBAC | Admin | ✅ PASS | 403 | 403 |
| ADM-SUB-005-NOAUTH | ADM-SUB-005-NOAUTH | Admin | ✅ PASS | 401 | 401 |
| ADM-SUB-006 | ADM-SUB-006 | Admin | ✅ PASS | 200 | 200 |
| ADM-FLG-001 | ADM-FLG-001 | Admin | ✅ PASS | 200 | 200 |
| ADM-FLG-001-NEG | ADM-FLG-001-NEG | Admin | ✅ PASS | 400 or 422 | 422 |
| ADM-FLG-002 | ADM-FLG-002 | Admin | ✅ PASS | 200 with flags array | 200 count:1 |
| ADM-FLG-003 | ADM-FLG-003 | Admin | ✅ PASS | 200 | 200 |
| ADM-FLG-003-RBAC | ADM-FLG-003-RBAC | Admin | ✅ PASS | 403 | 403 |
| ADM-POL-001 | ADM-POL-001 | Admin | ✅ PASS | 200 | 200 |
| ADM-POL-001-NEG | ADM-POL-001-NEG | Admin | ✅ PASS | 400 | 400 |
| ADM-POL-002 | ADM-POL-002 | Admin | ✅ PASS | 200 with allowed:boolean | 200 |
| ADM-POL-002-NEG | ADM-POL-002-NEG | Admin | ✅ PASS | 400 or 422 | 422 |
| ADM-POL-003 | ADM-POL-003 | Admin | ✅ PASS | 200 or 404 | 404 |
| ADM-TOK-001 | ADM-TOK-001 | Admin | ✅ PASS | 200 | 200 |
| ADM-TOK-002 | ADM-TOK-002 | Admin | ✅ PASS | 200 with logs array | 200 count:0 |
| ADM-TOK-002-NOAUTH | ADM-TOK-002-NOAUTH | Admin | ✅ PASS | 401 | 401 |
| AI-POST-001 | AI-POST-001 | AI-Intelligence | ✅ PASS | 200 with sanitized:string | 200 |
| AI-POST-002 | AI-POST-002 | AI-Intelligence | ✅ PASS | 200 with safe:boolean | 200 |
| AI-POST-003 | AI-POST-003 | AI-Intelligence | ✅ PASS | 200 | 200 |
| AI-GET-NEG-001 | AI-GET-NEG-001 | AI-Intelligence | ✅ PASS | 422 | 422 |
| AI-GET-NEG-002 | AI-GET-NEG-002 | AI-Intelligence | ✅ PASS | 401 | 401 |
| AI-POST-004-RBAC | AI-POST-004-RBAC | AI-Intelligence | ✅ PASS | 403 | 403 |
| GOV-001 | GOV-001 | Governance | ✅ PASS | 200 with valid:boolean or 403 denied | 403 |
| GOV-002 | GOV-002 | Governance | ✅ PASS | 200 or 403 | 403 |
| GOV-003 | GOV-003 | Governance | ✅ PASS | 200 with usage field or 403 denied | 403 |
| GOV-004 | GOV-004 | Governance | ✅ PASS | 400, 422, or 403 | 403 |
| GOV-006-NEG | GOV-006-NEG | Governance | ✅ PASS | 400, 422, or 403 | 403 |
| GOV-007-NEG | GOV-007-NEG | Governance | ✅ PASS | 422 or 403 | 403 |
| GOV-005 | GOV-005 | Governance | ✅ PASS | 401 | 401 |
| GOV-008-NEG | GOV-008-NEG | Governance | ✅ PASS | 401 | 401 |
| GOV-009-NEG | GOV-009-NEG | Governance | ✅ PASS | 401 | 401 |
| PERF-HEALTH-1 | PERF-HEALTH-1 | Performance | ✅ PASS | 200 | 200 (7ms) |
| PERF-HEALTH-2 | PERF-HEALTH-2 | Performance | ✅ PASS | 200 | 200 (7ms) |
| PERF-HEALTH-3 | PERF-HEALTH-3 | Performance | ✅ PASS | 200 | 200 (8ms) |
| PERF-HEALTH-4 | PERF-HEALTH-4 | Performance | ✅ PASS | 200 | 200 (7ms) |
| PERF-HEALTH-5 | PERF-HEALTH-5 | Performance | ✅ PASS | 200 | 200 (7ms) |
| PERF-HEALTH-6 | PERF-HEALTH-6 | Performance | ✅ PASS | 200 | 200 (6ms) |
| PERF-HEALTH-7 | PERF-HEALTH-7 | Performance | ✅ PASS | 200 | 200 (7ms) |
| PERF-HEALTH-8 | PERF-HEALTH-8 | Performance | ✅ PASS | 200 | 200 (6ms) |
| PERF-HEALTH-9 | PERF-HEALTH-9 | Performance | ✅ PASS | 200 | 200 (7ms) |
| PERF-HEALTH-10 | PERF-HEALTH-10 | Performance | ✅ PASS | 200 | 200 (7ms) |
| PERF-HEALTH-P95 | PERF-HEALTH-P95 | Performance | ✅ PASS | p95 < 1500ms | avg=7ms, p95=7ms |
| PERF-LOGIN-1 | PERF-LOGIN-1 | Performance | ✅ PASS | 200 | 200 (561ms) |
| PERF-LOGIN-2 | PERF-LOGIN-2 | Performance | ✅ PASS | 200 | 200 (589ms) |
| PERF-LOGIN-3 | PERF-LOGIN-3 | Performance | ✅ PASS | 200 | 200 (565ms) |
| PERF-LOGIN-4 | PERF-LOGIN-4 | Performance | ✅ PASS | 200 | 200 (589ms) |
| PERF-LOGIN-5 | PERF-LOGIN-5 | Performance | ✅ PASS | 200 | 200 (549ms) |
| PERF-LOGIN-P95 | PERF-LOGIN-P95 | Performance | ✅ PASS | p95 < 3000ms | p95=589ms |
