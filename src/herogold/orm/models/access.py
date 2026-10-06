"""Permission checks for users and roles.

A user holds a permission when any of their roles grants it, or failing that,
when it was granted to them directly. Soft-deleted links and permissions never count.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import col, select

from herogold.orm.core.errors import PermissionDeniedError
from herogold.orm.models.permission import Permission
from herogold.orm.models.role_permission import RolePermission
from herogold.orm.models.user_permission import UserPermission
from herogold.orm.models.user_role import UserRole

if TYPE_CHECKING:
    from herogold.orm.models.role import Role
    from herogold.orm.models.user import User


def role_has_permission(role: Role, resource: str, action: str) -> bool:
    """Return whether ``role`` grants the ``resource:action`` permission."""
    name = Permission.build_name(resource, action)
    query = (
        select(RolePermission.id)
        .join(Permission, col(Permission.id) == RolePermission.permission_id)
        .where(
            RolePermission.role_id == role.id,
            Permission.name == name,
            col(RolePermission.deleted_at).is_(None),
            col(Permission.deleted_at).is_(None),
        )
    )
    return Permission.session.exec(query).first() is not None


def user_has_permission(user: User, resource: str, action: str) -> bool:
    """Return whether ``user`` holds ``resource:action``, checking their roles before direct grants."""
    name = Permission.build_name(resource, action)
    return _granted_by_role(user, name) or _granted_directly(user, name)


def require_permission(user: User, resource: str, action: str) -> None:
    """Raise :class:`PermissionDeniedError` unless ``user`` holds ``resource:action``."""
    if not user_has_permission(user, resource, action):
        msg = f"User {user.username!r} lacks permission {Permission.build_name(resource, action)!r}."
        raise PermissionDeniedError(msg)


def _granted_by_role(user: User, permission_name: str) -> bool:
    """Return whether any of ``user``'s roles grants ``permission_name``."""
    query = (
        select(UserRole.id)
        .join(RolePermission, col(RolePermission.role_id) == UserRole.role_id)
        .join(Permission, col(Permission.id) == RolePermission.permission_id)
        .where(
            UserRole.user_id == user.id,
            Permission.name == permission_name,
            col(UserRole.deleted_at).is_(None),
            col(RolePermission.deleted_at).is_(None),
            col(Permission.deleted_at).is_(None),
        )
    )
    return Permission.session.exec(query).first() is not None


def _granted_directly(user: User, permission_name: str) -> bool:
    """Return whether ``permission_name`` was granted to ``user`` directly."""
    query = (
        select(UserPermission.id)
        .join(Permission, col(Permission.id) == UserPermission.permission_id)
        .where(
            UserPermission.user_id == user.id,
            Permission.name == permission_name,
            col(UserPermission.deleted_at).is_(None),
            col(Permission.deleted_at).is_(None),
        )
    )
    return Permission.session.exec(query).first() is not None
