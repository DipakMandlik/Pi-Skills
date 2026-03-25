from __future__ import annotations

from backend.v2.config.rbac import get_inherited_roles, has_permission


def test_owner_inherits_all():
    roles = get_inherited_roles("OWNER")
    assert "OWNER" in roles
    assert "ADMIN" in roles
    assert "MEMBER" in roles
    assert "VIEWER" in roles


def test_admin_inherits_member_viewer():
    roles = get_inherited_roles("ADMIN")
    assert "ADMIN" in roles
    assert "MEMBER" in roles
    assert "VIEWER" in roles
    assert "OWNER" not in roles


def test_member_inherits_viewer():
    roles = get_inherited_roles("MEMBER")
    assert "MEMBER" in roles
    assert "VIEWER" in roles
    assert "ADMIN" not in roles


def test_viewer_inherits_only_self():
    roles = get_inherited_roles("VIEWER")
    assert roles == {"VIEWER"}


def test_has_permission_owner_can_admin():
    assert has_permission("OWNER", "ADMIN") is True
    assert has_permission("OWNER", "MEMBER") is True
    assert has_permission("OWNER", "VIEWER") is True


def test_has_permission_admin():
    assert has_permission("ADMIN", "ADMIN") is True
    assert has_permission("ADMIN", "MEMBER") is True
    assert has_permission("ADMIN", "VIEWER") is True
    assert has_permission("ADMIN", "OWNER") is False


def test_has_permission_member():
    assert has_permission("MEMBER", "MEMBER") is True
    assert has_permission("MEMBER", "VIEWER") is True
    assert has_permission("MEMBER", "ADMIN") is False


def test_has_permission_viewer():
    assert has_permission("VIEWER", "VIEWER") is True
    assert has_permission("VIEWER", "MEMBER") is False


def test_has_permission_case_insensitive():
    assert has_permission("owner", "admin") is True
    assert has_permission("Admin", "viewer") is True
