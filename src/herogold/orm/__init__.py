"""Public exports for ORM package."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

__all__ = [
    "SELF",
    "BaseModel",
    "Configuration",
    "Email",
    "Password",
    "Permission",
    "QuerySet",
    "Relationship",
    "Repository",
    "Role",
    "RolePermission",
    "SelfRelationship",
    "Upserted",
    "User",
    "UserEmail",
    "UserPermission",
    "UserRole",
    "assert_statements",
    "configure",
    "count_statements",
    "forbid_unbatched_loads",
    "get_foreign_key",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BaseModel": ("orm.core.model", "BaseModel"),
    "SELF": ("orm.core.utils", "SELF"),
    "Relationship": ("orm.core.utils", "Relationship"),
    "SelfRelationship": ("orm.core.utils", "SelfRelationship"),
    "get_foreign_key": ("orm.core.utils", "get_foreign_key"),
    "configure": ("orm.core.configure", "configure"),
    "assert_statements": ("orm.testing", "assert_statements"),
    "count_statements": ("orm.testing", "count_statements"),
    "forbid_unbatched_loads": ("orm.testing", "forbid_unbatched_loads"),
    "QuerySet": ("orm.repository", "QuerySet"),
    "Repository": ("orm.repository", "Repository"),
    "Upserted": ("orm.repository", "Upserted"),
    "Configuration": ("orm.models.configuration", "Configuration"),
    "Email": ("orm.models.email", "Email"),
    "Password": ("orm.models.password", "Password"),
    "Permission": ("orm.models.permission", "Permission"),
    "Role": ("orm.models.role", "Role"),
    "RolePermission": ("orm.models.role_permission", "RolePermission"),
    "User": ("orm.models.user", "User"),
    "UserEmail": ("orm.models.user_email", "UserEmail"),
    "UserPermission": ("orm.models.user_permission", "UserPermission"),
    "UserRole": ("orm.models.user_role", "UserRole"),
}

if TYPE_CHECKING:
    # Static names for type checkers. At runtime `__getattr__` below imports lazily.
    from herogold.orm.core.configure import configure
    from herogold.orm.core.model import BaseModel
    from herogold.orm.core.utils import SELF, Relationship, SelfRelationship, get_foreign_key
    from herogold.orm.models.configuration import Configuration
    from herogold.orm.models.email import Email
    from herogold.orm.models.password import Password
    from herogold.orm.models.permission import Permission
    from herogold.orm.models.role import Role
    from herogold.orm.models.role_permission import RolePermission
    from herogold.orm.models.user import User
    from herogold.orm.models.user_email import UserEmail
    from herogold.orm.models.user_permission import UserPermission
    from herogold.orm.models.user_role import UserRole
    from herogold.orm.repository import QuerySet, Repository, Upserted
    from herogold.orm.testing import assert_statements, count_statements, forbid_unbatched_loads


def __getattr__(name: str) -> object:
    """Resolve public symbols lazily to avoid import-time side effects."""
    if name not in _EXPORTS:
        msg = f"module 'orm' has no attribute {name!r}"
        raise AttributeError(msg)

    module_name, attr_name = _EXPORTS[name]
    module = import_module(f"herogold.{module_name}")
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    """Return available module attributes for tab completion."""
    return sorted(set(globals()) | set(__all__))
