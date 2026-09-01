"""Public exports for ORM package."""

from importlib import import_module

__all__ = [
    "SELF",
    "BaseModel",
    "Configuration",
    "Email",
    "Password",
    "Permission",
    "Relationship",
    "Role",
    "RolePermission",
    "User",
    "UserEmail",
    "UserPermission",
    "UserRole",
    "get_foreign_key",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "BaseModel": ("orm.core.model", "BaseModel"),
    "SELF": ("orm.core.utils", "SELF"),
    "Relationship": ("orm.core.utils", "Relationship"),
    "get_foreign_key": ("orm.core.utils", "get_foreign_key"),
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


def __getattr__(name: str) -> object:
    """Resolve public symbols lazily to avoid import-time side effects."""
    if name not in _EXPORTS:
        msg = f"module 'orm' has no attribute {name!r}"
        raise AttributeError(msg)

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    """Return available module attributes for tab completion."""
    return sorted(set(globals()) | set(__all__))
