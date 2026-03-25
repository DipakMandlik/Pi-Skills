"""
RBAC Admin Router — Role management, permission queries, hierarchy inspection.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..middleware.rbac_middleware import require_admin
from ..services.rbac_service import RBACService

logger = logging.getLogger("backend.rbac_admin")

router = APIRouter(prefix="/rbac", tags=["rbac"])


# ── Request/Response Schemas ──────────────────────────────

class RoleAssignRequest(BaseModel):
    user_id: str
    role: str
    environment: str | None = None


class BulkRoleAssignRequest(BaseModel):
    user_ids: list[str]
    role: str


class AgentAccessCheckRequest(BaseModel):
    agent_id: str
    target_schema: str
    action: str


class EndpointAccessCheckRequest(BaseModel):
    user_id: str
    path: str
    method: str


# ── Role Management Endpoints ─────────────────────────────

@router.get("/roles")
async def list_roles(request: Request):
    """List all defined roles with descriptions and permissions."""
    require_admin(request)
    svc = RBACService(None)
    return {"roles": svc.get_all_roles()}


@router.get("/roles/hierarchy")
async def get_role_hierarchy(request: Request):
    """Get the complete role hierarchy tree."""
    require_admin(request)
    svc = RBACService(None)
    return svc.get_role_hierarchy()


@router.get("/roles/{role_name}/permissions")
async def get_role_permissions_endpoint(role_name: str, request: Request):
    """Get detailed permissions for a specific role."""
    require_admin(request)
    svc = RBACService(None)
    try:
        from ..core.rbac import get_role_permissions
        permissions = get_role_permissions(role_name)
        return permissions
    except Exception:
        raise HTTPException(status_code=404, detail=f"Role not found: {role_name}")


# ── User Role Management ──────────────────────────────────

@router.get("/users")
async def list_users_with_roles(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """List all users with their assigned roles."""
    require_admin(request)
    svc = RBACService(db)
    users = await svc.list_users_with_roles()
    return {"users": users, "total": len(users)}


@router.post("/users/assign-role")
async def assign_role(
    body: RoleAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Assign a role to a user."""
    admin = require_admin(request)
    svc = RBACService(db)
    try:
        result = await svc.assign_role(
            user_id=body.user_id,
            role=body.role,
            assigned_by=admin.user_id,
            environment=body.environment,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/bulk-assign-role")
async def bulk_assign_role(
    body: BulkRoleAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Assign a role to multiple users."""
    admin = require_admin(request)
    svc = RBACService(db)
    try:
        result = await svc.bulk_assign_role(
            user_ids=body.user_ids,
            role=body.role,
            assigned_by=admin.user_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Get the complete permission set for a user."""
    require_admin(request)
    svc = RBACService(db)
    try:
        perms = await svc.get_user_permissions(user_id)
        return perms
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Access Check Endpoints ────────────────────────────────

@router.post("/check/endpoint")
async def check_endpoint_access(
    body: EndpointAccessCheckRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Check if a user can access a specific API endpoint."""
    require_admin(request)
    svc = RBACService(db)
    result = await svc.check_endpoint_access(
        user_id=body.user_id,
        path=body.path,
        method=body.method,
    )
    return result


@router.post("/check/agent")
async def check_agent_access(
    body: AgentAccessCheckRequest,
    request: Request,
):
    """Validate AI agent access to a schema/action."""
    require_admin(request)
    svc = RBACService(None)
    return svc.check_agent_access(
        agent_id=body.agent_id,
        target_schema=body.target_schema,
        action=body.action,
    )


# ── Audit Endpoints ───────────────────────────────────────

@router.get("/audit/role-changes")
async def get_role_change_history(
    request: Request,
    user_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    """Get role change audit history."""
    require_admin(request)
    svc = RBACService(db)
    history = await svc.get_role_change_history(user_id=user_id, limit=limit)
    return {"history": history, "total": len(history)}
