from enum import Enum


class Role(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


ROLE_HIERARCHY: dict[str, list[str]] = {
    "OWNER": ["ADMIN", "MEMBER", "VIEWER"],
    "ADMIN": ["MEMBER", "VIEWER"],
    "MEMBER": ["VIEWER"],
    "VIEWER": [],
}


def get_inherited_roles(role: str) -> set[str]:
    role_upper = role.upper()
    inherited = {role_upper}
    queue = [role_upper]
    while queue:
        current = queue.pop(0)
        for child in ROLE_HIERARCHY.get(current, []):
            if child not in inherited:
                inherited.add(child)
                queue.append(child)
    return inherited


def has_permission(user_role: str, required_role: str) -> bool:
    inherited = get_inherited_roles(user_role.upper())
    return required_role.upper() in inherited
