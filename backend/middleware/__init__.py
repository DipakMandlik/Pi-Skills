"""
RBAC Middleware — Export both legacy and enhanced middleware.
"""
from .auth import JWTAuthMiddleware
from .rbac_middleware import (
    RBACAuthMiddleware,
    require_roles,
    require_admin,
    require_role_inheritance,
    require_agent_scope,
)

__all__ = [
    "JWTAuthMiddleware",
    "RBACAuthMiddleware",
    "require_roles",
    "require_admin",
    "require_role_inheritance",
    "require_agent_scope",
]
