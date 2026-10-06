from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from herogold.orm.core.errors import PermissionDeniedError
from herogold.orm.models.access import require_permission, role_has_permission, user_has_permission
from herogold.orm.models.permission import Permission
from herogold.orm.models.role import Role
from herogold.orm.models.role_permission import RolePermission
from herogold.orm.models.user import User
from herogold.orm.models.user_permission import UserPermission
from herogold.orm.models.user_role import UserRole

if TYPE_CHECKING:
    from sqlmodel import Session


def _permission(resource: str, action: str) -> Permission:
    permission = Permission(name="", resource="", action="")
    permission.set_from_parts(resource, action)
    permission.add()
    return permission


def _user(username: str) -> User:
    user = User(username=username)
    user.add()
    return user


def _role(name: str) -> Role:
    role = Role(name=name)
    role.add()
    return role


def test_user_gets_permission_through_role(session: Session) -> None:
    user, role, permission = _user("alice"), _role("editor"), _permission("Posts", "Edit")
    UserRole(user_id=user.id, role_id=role.id).add()
    RolePermission(role_id=role.id, permission_id=permission.id).add()

    assert role_has_permission(role, "posts", "edit")
    assert user_has_permission(user, "POSTS", "edit")


def test_user_gets_direct_permission(session: Session) -> None:
    user, permission = _user("bob"), _permission("posts", "delete")
    UserPermission(user_id=user.id, permission_id=permission.id).add()

    assert user_has_permission(user, "posts", "delete")


def test_user_without_grant_is_denied(session: Session) -> None:
    user, role = _user("carol"), _role("viewer")
    _permission("posts", "edit")
    UserRole(user_id=user.id, role_id=role.id).add()

    assert not user_has_permission(user, "posts", "edit")
    with pytest.raises(PermissionDeniedError, match="posts:edit"):
        require_permission(user, "posts", "edit")


def test_soft_deleted_grant_does_not_count(session: Session) -> None:
    user, permission = _user("dave"), _permission("posts", "edit")
    grant = UserPermission(user_id=user.id, permission_id=permission.id)
    grant.add()
    grant.delete()

    assert not user_has_permission(user, "posts", "edit")
