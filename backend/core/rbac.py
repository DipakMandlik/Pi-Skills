"""
RBAC Configuration — Role Definitions, Permission Matrix, Hierarchy
Enterprise-grade access control for AI-powered data platform.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ── Role Enum ──────────────────────────────────────────────

class PlatformRole(str, Enum):
    ORG_ADMIN = "ORG_ADMIN"
    SECURITY_ADMIN = "SECURITY_ADMIN"
    DATA_ENGINEER = "DATA_ENGINEER"
    ANALYTICS_ENGINEER = "ANALYTICS_ENGINEER"
    DATA_SCIENTIST = "DATA_SCIENTIST"
    BUSINESS_USER = "BUSINESS_USER"
    VIEWER = "VIEWER"
    SYSTEM_AGENT = "SYSTEM_AGENT"

    @classmethod
    def from_str(cls, value: str) -> PlatformRole:
        normalized = value.upper().strip()
        for member in cls:
            if member.value == normalized:
                return member
        return cls.VIEWER

    @classmethod
    def all_values(cls) -> list[str]:
        return [m.value for m in cls]


# ── Role Hierarchy ─────────────────────────────────────────

ROLE_HIERARCHY: dict[str, list[str]] = {
    "SYSADMIN":             ["ORG_ADMIN"],
    "ORG_ADMIN":            ["SECURITY_ADMIN", "DATA_ENGINEER", "SYSTEM_AGENT"],
    "DATA_ENGINEER":        ["ANALYTICS_ENGINEER"],
    "ANALYTICS_ENGINEER":   ["DATA_SCIENTIST"],
    "DATA_SCIENTIST":       ["BUSINESS_USER"],
    "BUSINESS_USER":        ["VIEWER"],
    "SECURITY_ADMIN":       [],
    "SYSTEM_AGENT":         [],
    "VIEWER":               [],
}


def get_inherited_roles(role: str) -> set[str]:
    """Return all roles inherited by the given role (including itself)."""
    role_upper = role.upper()
    inherited = {role_upper}
    for parent, children in ROLE_HIERARCHY.items():
        if _is_descendant(role_upper, parent):
            inherited.add(parent)
    return inherited


def _is_descendant(target: str, current: str) -> bool:
    """DFS to check if target is a descendant of current in the hierarchy."""
    for child in ROLE_HIERARCHY.get(current, []):
        if child == target or _is_descendant(target, child):
            return True
    return False


# ── Snowflake Resource Permissions ────────────────────────

@dataclass(frozen=True)
class ResourcePermission:
    resource_type: str          # WAREHOUSE, DATABASE, SCHEMA, TABLE, VIEW
    resource_name: str          # e.g. COMPUTE_WH, RAW_DB
    actions: tuple[str, ...]    # e.g. ("USAGE",), ("SELECT", "INSERT")
    scope: str = "ALL"          # ALL, SCHEMA, TABLE, VIEW, SECURE_VIEW


# Permission definitions per role
ROLE_SNOWFLAKE_PERMISSIONS: dict[str, list[ResourcePermission]] = {
    "ORG_ADMIN": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("ALL",)),
        ResourcePermission("WAREHOUSE", "TRANSFORM_WH", ("ALL",)),
        ResourcePermission("DATABASE", "RAW_DB", ("ALL",)),
        ResourcePermission("DATABASE", "STAGING_DB", ("ALL",)),
        ResourcePermission("DATABASE", "CURATED_DB", ("ALL",)),
        ResourcePermission("DATABASE", "SANDBOX_DB", ("ALL",)),
        ResourcePermission("DATABASE", "PUBLISHED_DB", ("ALL",)),
        ResourcePermission("DATABASE", "GOVERNANCE_DB", ("ALL",)),
    ],
    "SECURITY_ADMIN": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("USAGE",)),
        ResourcePermission("DATABASE", "GOVERNANCE_DB", ("ALL",)),
    ],
    "DATA_ENGINEER": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("USAGE",)),
        ResourcePermission("WAREHOUSE", "TRANSFORM_WH", ("USAGE", "MODIFY")),
        ResourcePermission("DATABASE", "RAW_DB", ("SELECT", "INSERT"), "TABLE"),
        ResourcePermission("DATABASE", "STAGING_DB", ("ALL",), "TABLE"),
    ],
    "ANALYTICS_ENGINEER": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("USAGE",)),
        ResourcePermission("WAREHOUSE", "TRANSFORM_WH", ("USAGE",)),
        ResourcePermission("DATABASE", "RAW_DB", ("SELECT",), "TABLE"),
        ResourcePermission("DATABASE", "STAGING_DB", ("SELECT", "INSERT"), "TABLE"),
        ResourcePermission("DATABASE", "CURATED_DB", ("ALL",), "TABLE"),
    ],
    "DATA_SCIENTIST": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("USAGE",)),
        ResourcePermission("DATABASE", "RAW_DB", ("SELECT",), "TABLE"),
        ResourcePermission("DATABASE", "CURATED_DB", ("SELECT",), "TABLE"),
        ResourcePermission("DATABASE", "SANDBOX_DB", ("ALL",), "TABLE"),
    ],
    "BUSINESS_USER": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("USAGE",)),
        ResourcePermission("DATABASE", "CURATED_DB", ("SELECT",), "VIEW"),
        ResourcePermission("DATABASE", "PUBLISHED_DB", ("SELECT",), "VIEW"),
    ],
    "VIEWER": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("USAGE",)),
        ResourcePermission("DATABASE", "PUBLISHED_DB", ("SELECT",), "VIEW"),
    ],
    "SYSTEM_AGENT": [
        ResourcePermission("WAREHOUSE", "COMPUTE_WH", ("USAGE",)),
        ResourcePermission("DATABASE", "RAW_DB", ("SELECT",), "TABLE"),
        ResourcePermission("DATABASE", "CURATED_DB", ("SELECT",), "VIEW"),
    ],
}


# ── API Endpoint Permissions ──────────────────────────────

@dataclass(frozen=True)
class APIPermission:
    path_pattern: str
    methods: tuple[str, ...]
    description: str = ""


ROLE_API_PERMISSIONS: dict[str, list[APIPermission]] = {
    "ORG_ADMIN": [
        APIPermission("/admin/*", ("GET", "POST", "PUT", "DELETE"), "Full admin access"),
        APIPermission("/rbac/*", ("GET", "POST"), "RBAC management"),
        APIPermission("/ai-intelligence/*", ("GET", "POST"), "AI intelligence governance access"),
        APIPermission("/pipeline/*", ("GET", "POST"), "Pipeline management"),
        APIPermission("/analytics/*", ("GET", "POST"), "Analytics access"),
        APIPermission("/agent/*", ("GET", "POST"), "Agent management"),
        APIPermission("/audit/*", ("GET",), "Audit log access"),
        APIPermission("/monitoring", ("GET",), "Monitoring access"),
        APIPermission("/execute", ("POST",), "Model execution"),
        APIPermission("/skills", ("GET", "POST", "PUT", "DELETE"), "Full skill management"),
        APIPermission("/skills/*", ("GET", "POST", "PUT", "PATCH", "DELETE"), "Full skill management"),
        APIPermission("/models", ("GET",), "View models"),
        APIPermission("/users/*", ("GET", "POST", "PUT", "DELETE"), "User management"),
        APIPermission("/orchestrate/*", ("GET", "POST"), "Multi-agent orchestration"),
    ],
    "SECURITY_ADMIN": [
        APIPermission("/admin/users", ("GET",), "User listing"),
        APIPermission("/admin/policies/*", ("GET", "POST", "PUT", "DELETE"), "Policy management"),
        APIPermission("/rbac/*", ("GET",), "RBAC read-only access"),
        APIPermission("/ai-intelligence/*", ("GET", "POST"), "AI intelligence governance access"),
        APIPermission("/skills", ("GET", "POST", "PUT", "DELETE"), "Skill management"),
        APIPermission("/skills/*", ("GET", "POST", "PUT", "PATCH", "DELETE"), "Skill management"),
        APIPermission("/audit/*", ("GET",), "Audit log access"),
        APIPermission("/admin/model-access/*", ("GET",), "Model access viewing"),
        APIPermission("/monitoring", ("GET",), "Monitoring access"),
        APIPermission("/execute", ("POST",), "Model execution"),
        APIPermission("/skills", ("GET",), "View skills"),
        APIPermission("/models", ("GET",), "View models"),
    ],
    "DATA_ENGINEER": [
        APIPermission("/pipeline/*", ("GET", "POST"), "Pipeline execution"),
        APIPermission("/ingest/*", ("GET", "POST"), "Data ingestion"),
        APIPermission("/skills", ("GET",), "View skills"),
        APIPermission("/models", ("GET",), "View models"),
        APIPermission("/execute", ("POST",), "Model execution"),
        APIPermission("/monitoring", ("GET",), "Own monitoring"),
        APIPermission("/orchestrate/*", ("GET", "POST"), "Multi-agent orchestration"),
    ],
    "ANALYTICS_ENGINEER": [
        APIPermission("/analytics/*", ("GET", "POST"), "Analytics and transforms"),
        APIPermission("/transform/*", ("GET", "POST"), "Transformation tasks"),
        APIPermission("/skills", ("GET",), "View skills"),
        APIPermission("/models", ("GET",), "View models"),
        APIPermission("/execute", ("POST",), "Model execution"),
        APIPermission("/monitoring", ("GET",), "Own monitoring"),
    ],
    "DATA_SCIENTIST": [
        APIPermission("/analytics/*", ("GET", "POST"), "Analytics access"),
        APIPermission("/models/*", ("GET", "POST"), "Model exploration"),
        APIPermission("/features/*", ("GET", "POST"), "Feature engineering"),
        APIPermission("/skills", ("GET",), "View skills"),
        APIPermission("/execute", ("POST",), "Model execution"),
        APIPermission("/monitoring", ("GET",), "Own monitoring"),
    ],
    "BUSINESS_USER": [
        APIPermission("/analytics/read", ("GET",), "Read-only analytics"),
        APIPermission("/dashboards/*", ("GET",), "Dashboard viewing"),
        APIPermission("/skills", ("GET",), "View assigned skills"),
        APIPermission("/models", ("GET",), "View assigned models"),
        APIPermission("/execute", ("POST",), "Model execution"),
        APIPermission("/monitoring", ("GET",), "Own monitoring"),
    ],
    "VIEWER": [
        APIPermission("/dashboards/view", ("GET",), "Dashboard viewing only"),
        APIPermission("/skills", ("GET",), "View assigned skills"),
        APIPermission("/models", ("GET",), "View assigned models"),
        APIPermission("/monitoring", ("GET",), "Own monitoring"),
    ],
    "SYSTEM_AGENT": [
        APIPermission("/agent/*", ("GET", "POST"), "Agent task execution"),
        APIPermission("/pipeline/execute", ("POST",), "Pipeline execution"),
        APIPermission("/monitoring", ("GET",), "Own monitoring"),
    ],
}


# ── Agent Scope Configuration ─────────────────────────────

AGENT_ALLOWED_SCHEMAS: dict[str, list[str]] = {
    "ingestion_agent":   ["RAW_DB.INGEST", "RAW_DB.RAW"],
    "transform_agent":   ["STAGING_DB.TRANSFORM", "STAGING_DB.CLEANSED"],
    "analytics_agent":   ["CURATED_DB.ANALYTICS", "CURATED_DB.MARTS"],
    "report_agent":      ["PUBLISHED_DB.VIEWS", "PUBLISHED_DB.REPORTS"],
    "quality_agent":     ["RAW_DB.RAW", "STAGING_DB.CLEANSED", "CURATED_DB.ANALYTICS"],
}

AGENT_ALLOWED_ACTIONS: dict[str, list[str]] = {
    "ingestion_agent":   ["SELECT", "INSERT"],
    "transform_agent":   ["SELECT", "INSERT", "UPDATE"],
    "analytics_agent":   ["SELECT"],
    "report_agent":      ["SELECT"],
    "quality_agent":     ["SELECT"],
}


# ── Environment Scope ─────────────────────────────────────

ROLE_ENV_SCOPE: dict[str, list[str]] = {
    "ORG_ADMIN":          ["DEV", "QA", "PROD"],
    "SECURITY_ADMIN":     ["DEV", "QA", "PROD"],
    "DATA_ENGINEER":      ["DEV", "QA"],
    "ANALYTICS_ENGINEER": ["DEV", "QA", "PROD"],
    "DATA_SCIENTIST":     ["DEV", "QA"],
    "BUSINESS_USER":      ["PROD"],
    "VIEWER":             ["PROD"],
    "SYSTEM_AGENT":       ["PROD"],
}


# ── Role Descriptions ─────────────────────────────────────

ROLE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "ORG_ADMIN": {
        "label": "Organization Admin",
        "description": "Full platform governance, user lifecycle management, all DDL/DML",
        "data_boundary": "All databases, all schemas",
        "responsibilities": "Platform governance, user lifecycle, audit oversight",
    },
    "SECURITY_ADMIN": {
        "label": "Security Admin",
        "description": "IAM management, masking policies, audit monitoring",
        "data_boundary": "Governance and security schemas only",
        "responsibilities": "Identity access management, policy enforcement, security audit",
    },
    "DATA_ENGINEER": {
        "label": "Data Engineer",
        "description": "Pipeline build and operations, data ingestion",
        "data_boundary": "RAW and STAGING databases",
        "responsibilities": "Data pipeline development, ingestion, staging transformations",
    },
    "ANALYTICS_ENGINEER": {
        "label": "Analytics Engineer",
        "description": "dbt models, curated layer management, transformations",
        "data_boundary": "STAGING, CURATED databases",
        "responsibilities": "Data modeling, dbt transformations, curated layer build",
    },
    "DATA_SCIENTIST": {
        "label": "Data Scientist",
        "description": "Exploration, ML feature tables, experimentation",
        "data_boundary": "CURATED, FEATURES, SANDBOX databases",
        "responsibilities": "Data exploration, feature engineering, ML model development",
    },
    "BUSINESS_USER": {
        "label": "Business User",
        "description": "Self-serve analytics, dashboard consumption",
        "data_boundary": "CURATED views and PUBLISHED views",
        "responsibilities": "Business analytics, dashboard consumption, self-serve reporting",
    },
    "VIEWER": {
        "label": "Viewer",
        "description": "Read-only dashboard and report access",
        "data_boundary": "PUBLISHED views only",
        "responsibilities": "Report viewing, dashboard monitoring",
    },
    "SYSTEM_AGENT": {
        "label": "System Agent (AI)",
        "description": "AI-agent autonomous tasks with scoped access",
        "data_boundary": "Agent-specific schemas only, no DDL",
        "responsibilities": "Autonomous AI task execution within strict scope",
    },
}


# ── Helper Functions ───────────────────────────────────────

def get_role_permissions(role: str) -> dict:
    """Get complete permission set for a role."""
    role_upper = role.upper()
    return {
        "role": role_upper,
        "description": ROLE_DESCRIPTIONS.get(role_upper, {}),
        "snowflake_permissions": [
            {"resource_type": p.resource_type, "resource_name": p.resource_name,
             "actions": list(p.actions), "scope": p.scope}
            for p in ROLE_SNOWFLAKE_PERMISSIONS.get(role_upper, [])
        ],
        "api_permissions": [
            {"path": p.path_pattern, "methods": list(p.methods), "description": p.description}
            for p in ROLE_API_PERMISSIONS.get(role_upper, [])
        ],
        "environment_scope": ROLE_ENV_SCOPE.get(role_upper, []),
        "inherited_roles": list(get_inherited_roles(role_upper)),
    }


def can_access_api_endpoint(role: str, path: str, method: str) -> bool:
    """Check if a role can access a specific API endpoint."""
    role_upper = role.upper()
    permissions = ROLE_API_PERMISSIONS.get(role_upper, [])
    for perm in permissions:
        if _path_matches(path, perm.path_pattern) and method.upper() in perm.methods:
            return True
    return False


def _path_matches(path: str, pattern: str) -> bool:
    """Match API path against pattern (supports wildcard *)."""
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        if path.startswith(prefix):
            return True
        # Treat patterns like /users/* as matching /users too.
        if prefix.endswith("/") and path == prefix[:-1]:
            return True
        return False
    return path == pattern


def validate_agent_access(agent_id: str, target_schema: str, action: str) -> bool:
    """Validate if an AI agent can perform an action on a target schema."""
    allowed_schemas = AGENT_ALLOWED_SCHEMAS.get(agent_id, [])
    allowed_actions = AGENT_ALLOWED_ACTIONS.get(agent_id, [])

    if target_schema not in allowed_schemas:
        return False
    if action.upper() not in allowed_actions:
        return False
    return True


def get_role_for_snowflake_grant_query(role: str) -> str:
    """Return the SQL grant statement template for a role."""
    return f"GRANT ROLE {role.upper()} TO USER <username>;"
