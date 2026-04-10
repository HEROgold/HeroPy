"""ORM table models."""

from importlib import import_module

__all__ = [
    "Configuration",
    "Email",
    "Password",
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserEmail",
    "UserPermission",
    "UserRole",
]

_EXPORTS: dict[str, str] = {
    "Configuration": "orm.models.configuration",
    "Email": "orm.models.email",
    "Password": "orm.models.password",
    "Permission": "orm.models.permission",
    "Role": "orm.models.role",
    "RolePermission": "orm.models.role_permission",
    "User": "orm.models.user",
    "UserEmail": "orm.models.user_email",
    "UserPermission": "orm.models.user_permission",
    "UserRole": "orm.models.user_role",
}


def __getattr__(name: str) -> object:
    """Resolve model symbols lazily."""
    if name not in _EXPORTS:
        msg = f"module 'orm.models' has no attribute {name!r}"
        raise AttributeError(msg)

    module = import_module(_EXPORTS[name])
    return getattr(module, name)


def __dir__() -> list[str]:
    """Return available model names for tab completion."""
    return sorted(set(globals()) | set(__all__))
