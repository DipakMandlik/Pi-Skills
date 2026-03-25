"""
RBAC Service — Role management, permission resolution, audit logging.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import UserModel
from ..core.rbac import (
    AGENT_ALLOWED_ACTIONS,
    AGENT_ALLOWED_SCHEMAS,
    ROLE_DESCRIPTIONS,
    ROLE_ENV_SCOPE,
    ROLE_HIERARCHY,
    PlatformRole,
    can_access_api_endpoint,
    get_role_permissions,
    validate_agent_access,
)
from ..core.redis_client import cache_delete, cache_get, cache_set

logger = logging.getLogger("backend.rbac_service")

# Cache TTLs
_ROLE_CACHE_TTL = 300    # 5 minutes
_PERM_CACHE_TTL = 60     # 1 minute


class RBACService:
    """Service for RBAC operations: role assignment, permission checks, audit."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Role Assignment ────────────────────────────────────

    async def assign_role(
        self,
        user_id: str,
        role: str,
        assigned_by: str,
        environment: str | None = None,
    ) -> dict:
        """Assign a platform role to a user."""
        role_upper = role.upper()
        valid_roles = PlatformRole.all_values()
        if role_upper not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of: {valid_roles}")

        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        old_role = user.platform_role
        await self.db.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(platform_role=role_upper)
        )
        await self.db.commit()
        await self.db.refresh(user)

        # Invalidate permission cache
        await cache_delete(f"perm:{user_id}")
        await cache_delete(f"role:{user_id}")

        logger.info(
            "Role assigned: user=%s role=%s old_role=%s by=%s env=%s",
            user.email, role_upper, old_role, assigned_by, environment,
        )

        return {
            "user_id": user_id,
            "email": user.email,
            "old_role": old_role,
            "new_role": role_upper,
            "assigned_by": assigned_by,
            "assigned_at": datetime.now(UTC).isoformat(),
            "environment": environment,
        }

    async def bulk_assign_role(
        self,
        user_ids: list[str],
        role: str,
        assigned_by: str,
    ) -> dict:
        """Assign a role to multiple users."""
        assigned = []
        failed = []

        for user_id in user_ids:
            try:
                result = await self.assign_role(user_id, role, assigned_by)
                assigned.append(result)
            except ValueError as e:
                failed.append({"user_id": user_id, "error": str(e)})

        return {
            "assigned": assigned,
            "failed": failed,
            "total": len(user_ids),
            "success_count": len(assigned),
            "failure_count": len(failed),
        }

    # ── Permission Resolution ──────────────────────────────

    async def get_user_permissions(self, user_id: str) -> dict:
        """Get complete permission set for a user."""
        cache_key = f"perm:{user_id}"
        cached = await cache_get(cache_key)
        if cached:
            return cached

        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        role = user.platform_role.upper()
        permissions = get_role_permissions(role)
        permissions["user_id"] = user_id
        permissions["email"] = user.email
        permissions["is_active"] = user.is_active

        await cache_set(cache_key, permissions, ttl=_PERM_CACHE_TTL)
        return permissions

    async def check_endpoint_access(
        self,
        user_id: str,
        path: str,
        method: str,
    ) -> dict:
        """Check if a user can access a specific API endpoint."""
        result = await self.db.execute(
            select(UserModel.platform_role).where(UserModel.id == user_id)
        )
        role = result.scalar_one_or_none()
        if role is None:
            return {"allowed": False, "reason": "User not found"}

        allowed = can_access_api_endpoint(role, path, method)
        return {
            "allowed": allowed,
            "role": role,
            "path": path,
            "method": method,
            "reason": "Access granted" if allowed else f"Role {role} not authorized for {method} {path}",
        }

    # ── Agent Scope Validation ─────────────────────────────

    def check_agent_access(
        self,
        agent_id: str,
        target_schema: str,
        action: str,
    ) -> dict:
        """Validate AI agent access to a schema/action."""
        allowed = validate_agent_access(agent_id, target_schema, action)
        return {
            "agent_id": agent_id,
            "target_schema": target_schema,
            "action": action,
            "allowed": allowed,
            "allowed_schemas": AGENT_ALLOWED_SCHEMAS.get(agent_id, []),
            "allowed_actions": AGENT_ALLOWED_ACTIONS.get(agent_id, []),
        }

    # ── Role Listing & Info ────────────────────────────────

    async def list_users_with_roles(self) -> list[dict]:
        """List all users with their current roles."""
        result = await self.db.execute(
            select(UserModel).where(UserModel.is_active == True)
        )
        users = result.scalars().all()

        return [
            {
                "user_id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "role": u.platform_role,
                "is_active": u.is_active,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ]

    def get_all_roles(self) -> list[dict]:
        """Get all defined roles with descriptions and permissions."""
        roles = []
        for role_name in PlatformRole.all_values():
            info = ROLE_DESCRIPTIONS.get(role_name, {})
            roles.append({
                "role": role_name,
                "label": info.get("label", role_name),
                "description": info.get("description", ""),
                "responsibilities": info.get("responsibilities", ""),
                "data_boundary": info.get("data_boundary", ""),
                "environment_scope": ROLE_ENV_SCOPE.get(role_name, []),
                "parent_roles": [
                    parent for parent, children in ROLE_HIERARCHY.items()
                    if role_name in children
                ],
                "child_roles": ROLE_HIERARCHY.get(role_name, []),
            })
        return roles

    def get_role_hierarchy(self) -> dict:
        """Return the full role hierarchy tree."""
        return {
            "hierarchy": ROLE_HIERARCHY,
            "roots": ["SYSADMIN"],
            "leaf_roles": ["VIEWER", "SECURITY_ADMIN", "SYSTEM_AGENT"],
        }

    # ── Audit ──────────────────────────────────────────────

    async def get_role_change_history(
        self,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get role change history (from audit log)."""
        # In production, query GOVERNANCE_DB.AUDIT.RBAC_AUDIT_LOG
        # For now, return from local audit if available
        from ..core.database import AuditLogModel

        query = select(AuditLogModel).where(
            AuditLogModel.action.in_(["ROLE_ASSIGN", "ROLE_REVOKE"])
        ).order_by(AuditLogModel.timestamp.desc()).limit(limit)

        if user_id:
            query = query.where(AuditLogModel.user_id == user_id)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.action,
                "outcome": log.outcome,
                "metadata": log.metadata_,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ]


class RBACServiceError(Exception):
    pass
