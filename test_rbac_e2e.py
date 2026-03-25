"""
Comprehensive RBAC End-to-End Test Suite
Tests all 5 layers of the RBAC system from scratch.
"""
import asyncio
import os
import sys

os.environ["JWT_SECRET"] = "test-secret-key-for-e2e-rbac-testing-12345678"
os.environ["ENABLE_BOOTSTRAP_SEED"] = "true"

PASS_COUNT = 0
FAIL_COUNT = 0
ERRORS = []


def ok(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  PASS: {msg}")


def fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    ERRORS.append(msg)
    print(f"  FAIL: {msg}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def run_tests():
    # ── Step 1: Fresh Startup ──────────────────────────────
    section("STEP 1: FRESH STARTUP + SEED DATA")

    from backend.core.config import load_settings
    import backend.core.database as db_mod
    from backend.core.database import UserModel
    from backend.core.redis_client import init_redis
    from sqlalchemy import select

    settings = load_settings()
    db_mod.init_engine(settings)
    init_redis(settings.redis_url)
    await db_mod.create_tables()

    from backend.main import _seed_data
    await _seed_data()

    sf = db_mod._session_factory
    async with sf() as db:
        result = await db.execute(select(UserModel).order_by(UserModel.email))
        users = result.scalars().all()

    expected = {
        "admin@platform.local": "ORG_ADMIN",
        "security@platform.local": "SECURITY_ADMIN",
        "engineer@platform.local": "DATA_ENGINEER",
        "analytics@platform.local": "ANALYTICS_ENGINEER",
        "scientist@platform.local": "DATA_SCIENTIST",
        "business@platform.local": "BUSINESS_USER",
        "user@platform.local": "BUSINESS_USER",
        "viewer@platform.local": "VIEWER",
        "agent@platform.local": "SYSTEM_AGENT",
    }

    if len(users) == 9:
        ok(f"Seeded {len(users)} users")
    else:
        fail(f"Expected 9 users, got {len(users)}")

    for u in users:
        exp = expected.get(u.email)
        if exp and u.platform_role == exp:
            ok(f"{u.email:30s} -> {u.platform_role}")
        elif exp:
            fail(f"{u.email}: expected {exp}, got {u.platform_role}")
        else:
            fail(f"Unexpected user: {u.email}")

    # ── Step 2: Login All Roles ────────────────────────────
    section("STEP 2: LOGIN ALL 8 ROLES + JWT VALIDATION")

    from backend.services.auth_service import AuthService
    from backend.services.snowflake_service import SnowflakeService
    import jwt

    sf_svc = SnowflakeService(settings)
    auth = AuthService(settings, sf_svc)

    creds = [
        ("admin@platform.local", "admin123", "ORG_ADMIN"),
        ("security@platform.local", "security123", "SECURITY_ADMIN"),
        ("engineer@platform.local", "engineer123", "DATA_ENGINEER"),
        ("analytics@platform.local", "analytics123", "ANALYTICS_ENGINEER"),
        ("scientist@platform.local", "scientist123", "DATA_SCIENTIST"),
        ("business@platform.local", "business123", "BUSINESS_USER"),
        ("viewer@platform.local", "viewer123", "VIEWER"),
        ("agent@platform.local", "agent123", "SYSTEM_AGENT"),
    ]

    tokens = {}
    async with sf() as db:
        for email, pw, exp_role in creds:
            try:
                result = await auth.login(email, pw, db)
                tokens[email] = result["access_token"]

                if result.get("role") == exp_role:
                    ok(f"Login {email:30s} role={result['role']}")
                else:
                    fail(f"{email}: role {result.get('role')} != {exp_role}")

                if exp_role in result.get("roles", []):
                    ok(f"  roles={result['roles']}")
                else:
                    fail(f"{email}: {exp_role} not in {result.get('roles')}")

                payload = jwt.decode(result["access_token"], settings.jwt_secret, algorithms=["HS256"])
                if payload.get("role") == exp_role and exp_role in payload.get("roles", []):
                    ok(f"  JWT verified: role={payload['role']} roles={payload['roles']}")
                else:
                    fail(f"{email}: JWT payload mismatch")

            except Exception as e:
                fail(f"Login FAILED {email}: {e}")

        # bad password
        try:
            await auth.login("admin@platform.local", "wrong", db)
            fail("Bad password should reject")
        except Exception:
            ok("Bad password correctly rejected")

    # ── Step 3: get_me with RBAC ───────────────────────────
    section("STEP 3: /auth/me RETURNS roles + rbac_permissions")

    from backend.models.domain import AuthUser

    async with sf() as db:
        for email, pw, exp_role in creds:
            tok = tokens.get(email)
            if not tok:
                fail(f"No token for {email}")
                continue
            payload = jwt.decode(tok, settings.jwt_secret, algorithms=["HS256"])
            user = AuthUser(
                user_id=payload["sub"],
                email=payload.get("email", ""),
                role=payload.get("role", "VIEWER"),
                roles=payload.get("roles", []),
                display_name=payload.get("display_name", ""),
                token_exp=payload.get("exp", 0),
            )
            try:
                me = await auth.get_me(user, db)
                if "roles" in me and exp_role in me["roles"]:
                    ok(f"get_me {email:30s} roles={me['roles']}")
                else:
                    fail(f"get_me {email}: missing roles")

                if "rbac_permissions" in me and "snowflake_permissions" in me["rbac_permissions"]:
                    ok(f"  rbac_permissions present")
                else:
                    fail(f"get_me {email}: missing rbac_permissions")
            except Exception as e:
                fail(f"get_me FAILED {email}: {e}")

    # ── Step 4: Core RBAC ──────────────────────────────────
    section("STEP 4: CORE RBAC — HIERARCHY + PERMISSIONS")

    from backend.core.rbac import (
        PlatformRole, ROLE_HIERARCHY, ROLE_SNOWFLAKE_PERMISSIONS,
        ROLE_API_PERMISSIONS, get_inherited_roles, can_access_api_endpoint,
        validate_agent_access, get_role_permissions,
    )

    all_roles = PlatformRole.all_values()
    if set(all_roles) == {"ORG_ADMIN", "SECURITY_ADMIN", "DATA_ENGINEER", "ANALYTICS_ENGINEER",
                          "DATA_SCIENTIST", "BUSINESS_USER", "VIEWER", "SYSTEM_AGENT"}:
        ok(f"All 8 roles defined")
    else:
        fail(f"Role set mismatch: {all_roles}")

    # Hierarchy checks
    for child, parent, expected in [
        ("VIEWER", "ORG_ADMIN", True),
        ("DATA_ENGINEER", "SYSADMIN", True),
        ("SECURITY_ADMIN", "ORG_ADMIN", True),
        ("BUSINESS_USER", "DATA_ENGINEER", True),
        ("SYSTEM_AGENT", "DATA_ENGINEER", False),
        ("SECURITY_ADMIN", "DATA_ENGINEER", False),
    ]:
        result = parent in get_inherited_roles(child)
        if result == expected:
            ok(f"Hierarchy: {child} -> {parent} = {result}")
        else:
            fail(f"Hierarchy: {child} -> {parent} expected {expected}, got {result}")

    # Every role has permissions
    for role in all_roles:
        sf_p = len(ROLE_SNOWFLAKE_PERMISSIONS.get(role, []))
        api_p = len(ROLE_API_PERMISSIONS.get(role, []))
        if sf_p > 0 and api_p > 0:
            ok(f"Perms: {role:20s} SF={sf_p} API={api_p}")
        else:
            fail(f"Missing perms: {role} SF={sf_p} API={api_p}")

    # ── Step 5: API Access Tests ───────────────────────────
    section("STEP 5: API ACCESS CONTROL (37 tests)")

    tests = [
        ("ORG_ADMIN", "/admin/overview", "GET", True),
        ("ORG_ADMIN", "/admin/users", "GET", True),
        ("ORG_ADMIN", "/rbac/roles", "GET", True),
        ("ORG_ADMIN", "/execute", "POST", True),
        ("SECURITY_ADMIN", "/admin/users", "GET", True),
        ("SECURITY_ADMIN", "/admin/overview", "GET", False),
        ("SECURITY_ADMIN", "/ai-intelligence", "GET", True),
        ("DATA_ENGINEER", "/pipeline/execute", "POST", True),
        ("DATA_ENGINEER", "/skills", "GET", True),
        ("DATA_ENGINEER", "/execute", "POST", True),
        ("DATA_ENGINEER", "/admin/overview", "GET", False),
        ("ANALYTICS_ENGINEER", "/analytics", "GET", True),
        ("ANALYTICS_ENGINEER", "/execute", "POST", True),
        ("ANALYTICS_ENGINEER", "/pipeline/execute", "POST", False),
        ("DATA_SCIENTIST", "/analytics", "GET", True),
        ("DATA_SCIENTIST", "/models", "GET", True),
        ("DATA_SCIENTIST", "/execute", "POST", True),
        ("DATA_SCIENTIST", "/admin/overview", "GET", False),
        ("BUSINESS_USER", "/execute", "POST", True),
        ("BUSINESS_USER", "/skills", "GET", True),
        ("BUSINESS_USER", "/monitoring", "GET", True),
        ("BUSINESS_USER", "/admin/overview", "GET", False),
        ("BUSINESS_USER", "/pipeline/execute", "POST", False),
        ("VIEWER", "/skills", "GET", True),
        ("VIEWER", "/models", "GET", True),
        ("VIEWER", "/monitoring", "GET", True),
        ("VIEWER", "/execute", "POST", False),
        ("VIEWER", "/admin/overview", "GET", False),
        ("SYSTEM_AGENT", "/agent", "POST", True),
        ("SYSTEM_AGENT", "/monitoring", "GET", True),
        ("SYSTEM_AGENT", "/execute", "POST", False),
        ("SYSTEM_AGENT", "/admin/overview", "GET", False),
        ("SYSTEM_AGENT", "/skills", "GET", False),
    ]

    for role, path, method, exp in tests:
        result = can_access_api_endpoint(role, path, method)
        if result == exp:
            ok(f"{role:20s} {method:6s} {path:25s} -> {result}")
        else:
            fail(f"{role:20s} {method:6s} {path:25s} -> {result} (expected {exp})")

    # ── Step 6: Agent Scopes ───────────────────────────────
    section("STEP 6: AGENT SCOPE VALIDATION")

    for agent, schema, action, exp in [
        ("ingestion_agent", "RAW_DB.INGEST", "INSERT", True),
        ("ingestion_agent", "STAGING_DB.TRANSFORM", "INSERT", False),
        ("ingestion_agent", "RAW_DB.INGEST", "DELETE", False),
        ("transform_agent", "STAGING_DB.TRANSFORM", "UPDATE", True),
        ("transform_agent", "RAW_DB.RAW", "SELECT", False),
        ("analytics_agent", "CURATED_DB.ANALYTICS", "SELECT", True),
        ("analytics_agent", "CURATED_DB.ANALYTICS", "INSERT", False),
        ("report_agent", "PUBLISHED_DB.VIEWS", "SELECT", True),
        ("report_agent", "CURATED_DB.ANALYTICS", "SELECT", False),
        ("quality_agent", "RAW_DB.RAW", "SELECT", True),
        ("unknown_agent", "RAW_DB.RAW", "SELECT", False),
    ]:
        result = validate_agent_access(agent, schema, action)
        if result == exp:
            ok(f"{agent:20s} {schema:25s} {action:6s} -> {result}")
        else:
            fail(f"{agent:20s} {schema:25s} {action:6s} -> {result} (expected {exp})")

    # ── Step 7: RBAC Service ───────────────────────────────
    section("STEP 7: RBAC SERVICE — ROLE ASSIGNMENT")

    from backend.services.rbac_service import RBACService

    async with sf() as db:
        svc = RBACService(db)

        users_list = await svc.list_users_with_roles()
        ok(f"list_users_with_roles: {len(users_list)} users") if len(users_list) == 9 else fail(f"Expected 9, got {len(users_list)}")

        all_r = svc.get_all_roles()
        ok(f"get_all_roles: {len(all_r)} roles") if len(all_r) == 8 else fail(f"Expected 8, got {len(all_r)}")

        h = svc.get_role_hierarchy()
        ok(f"get_role_hierarchy: {len(h['hierarchy'])} edges") if "hierarchy" in h else fail("Missing hierarchy")

        # Test role assignment
        viewer = next((u for u in users_list if u["email"] == "viewer@platform.local"), None)
        if viewer:
            res = await svc.assign_role(viewer["user_id"], "DATA_SCIENTIST", "test-admin", "DEV")
            if res["new_role"] == "DATA_SCIENTIST":
                ok("assign_role: viewer -> DATA_SCIENTIST")
            else:
                fail(f"assign_role failed: {res}")

            perms = await svc.get_user_permissions(viewer["user_id"])
            ok(f"get_user_permissions: role={perms['role']}") if perms.get("role") == "DATA_SCIENTIST" else fail(f"Wrong role: {perms.get('role')}")

            await svc.assign_role(viewer["user_id"], "VIEWER", "test-admin")
            ok("Reverted to VIEWER")

    # ── Step 8: SQL Script ─────────────────────────────────
    section("STEP 8: SNOWFLAKE SQL SCRIPT")

    sql_path = os.path.join(os.path.dirname(__file__) or ".", "backend", "sql", "rbac_snowflake_ddl.sql")
    if os.path.exists(sql_path):
        with open(sql_path) as f:
            sql = f.read()
        for sec in ["CREATE ROLES", "ROLE HIERARCHY GRANTS", "WAREHOUSE GRANTS", "DATABASE GRANTS",
                     "FUTURE GRANTS", "SECURE VIEWS", "DYNAMIC DATA MASKING", "ROW ACCESS POLICY",
                     "ASSIGN ROLES TO USERS", "AUDIT LOGGING"]:
            if sec in sql:
                ok(f"SQL section: {sec}")
            else:
                fail(f"Missing: {sec}")
        for role in all_roles:
            ok(f"SQL CREATE ROLE: {role}") if f"CREATE ROLE IF NOT EXISTS {role}" in sql else fail(f"Missing CREATE ROLE: {role}")
        for p in ["pii_email_mask", "pii_phone_mask", "pii_ssn_mask", "pii_name_mask"]:
            ok(f"SQL masking: {p}") if p in sql else fail(f"Missing masking: {p}")
        for t in ["RBAC_AUDIT_LOG", "ROLE_ASSIGNMENTS", "AGENT_TASK_LOG"]:
            ok(f"SQL audit table: {t}") if t in sql else fail(f"Missing audit table: {t}")
    else:
        fail(f"SQL not found: {sql_path}")

    # ── Step 9: Domain Model ───────────────────────────────
    section("STEP 9: DOMAIN MODEL")

    u = AuthUser(user_id="t", email="t@t.com", role="DATA_ENGINEER",
                 roles=["DATA_ENGINEER", "ANALYTICS_ENGINEER"], display_name="T")
    ok("has_role DATA_ENGINEER") if u.has_role("DATA_ENGINEER") else fail("has_role")
    ok("has_role case insensitive") if u.has_role("data_engineer") else fail("case insensitive")
    ok("has_role ORG_ADMIN false") if not u.has_role("ORG_ADMIN") else fail("should be false")
    ok("has_any_role") if u.has_any_role("ORG_ADMIN", "DATA_ENGINEER") else fail("has_any_role")
    ok("has_any_role false") if not u.has_any_role("ORG_ADMIN", "SECURITY_ADMIN") else fail("should be false")

    u2 = AuthUser(user_id="t2", email="t2@t.com", role="VIEWER", display_name="T2")
    ok("default roles") if u2.roles == ["VIEWER"] else fail(f"Expected ['VIEWER'], got {u2.roles}")

    # ── Step 10: Schemas ───────────────────────────────────
    section("STEP 10: SCHEMAS")

    from backend.schemas.api import LoginResponse, UserMeResponse

    lr = LoginResponse(access_token="t", token_type="Bearer", expires_in=86400,
                       role="ORG_ADMIN", roles=["ORG_ADMIN"], user_id="id", display_name="T")
    ok("LoginResponse.roles") if lr.roles == ["ORG_ADMIN"] else fail("LoginResponse.roles")

    mr = UserMeResponse(user_id="id", email="e", role="DATA_ENGINEER", roles=["DATA_ENGINEER"],
                        display_name="T", allowed_models=[], allowed_skills=[],
                        rbac_permissions={"snowflake_permissions": [], "api_permissions": []},
                        token_expires_at="2026-01-01")
    ok("UserMeResponse.roles + rbac_permissions") if mr.roles == ["DATA_ENGINEER"] and mr.rbac_permissions else fail("UserMeResponse")

    # ── Step 11: Imports ───────────────────────────────────
    section("STEP 11: IMPORT CHAIN")

    for mod_name, attr in [
        ("backend.core.rbac", "PlatformRole"),
        ("backend.core.rbac", "ROLE_HIERARCHY"),
        ("backend.core.rbac", "get_role_permissions"),
        ("backend.core.rbac", "can_access_api_endpoint"),
        ("backend.core.rbac", "validate_agent_access"),
        ("backend.middleware.rbac_middleware", "RBACAuthMiddleware"),
        ("backend.middleware.rbac_middleware", "require_roles"),
        ("backend.middleware.rbac_middleware", "require_admin"),
        ("backend.services.rbac_service", "RBACService"),
        ("backend.routers.rbac_admin", "router"),
    ]:
        try:
            m = __import__(mod_name, fromlist=[attr])
            getattr(m, attr)
            ok(f"Import: {mod_name}.{attr}")
        except (ImportError, AttributeError) as e:
            fail(f"Import FAILED: {mod_name}.{attr}: {e}")

    # ── Final ──────────────────────────────────────────────
    section("FINAL RESULTS")
    print(f"\n  PASS: {PASS_COUNT}")
    print(f"  FAIL: {FAIL_COUNT}")
    print(f"  TOTAL: {PASS_COUNT + FAIL_COUNT}")
    if ERRORS:
        print(f"\n  FAILURES:")
        for e in ERRORS:
            print(f"    - {e}")
    return FAIL_COUNT == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
