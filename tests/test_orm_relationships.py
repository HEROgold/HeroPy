from __future__ import annotations

import sys
from configparser import ConfigParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORM_SRC = ROOT / "herogold" / "src"
if str(ORM_SRC) not in sys.path:
    sys.path.insert(0, str(ORM_SRC))

from herogold.orm.core.config import DbConfig  # noqa: E402
from herogold.orm.core.utils import get_foreign_key  # noqa: E402
from herogold.orm.models import (  # noqa: E402
    Configuration,
    Email,
    Password,
    Permission,
    Role,
    RolePermission,
    User,
    UserEmail,
    UserPermission,
    UserRole,
)

PARSER = ConfigParser()
PARSER.read(ROOT / "db_config.ini", encoding="utf-8")
DbConfig.set_parser(PARSER)


def test_get_foreign_key_matches_model_tablename() -> None:
    assert get_foreign_key(User) == "user.id"
    assert get_foreign_key(Email) == "email.id"
    assert get_foreign_key(Role, "name") == "role.name"


def test_optional_relationship_allows_none() -> None:
    user = User(username="alice", primary_email_id=None)

    assert user.primary_email is None


def test_relationship_returns_instance_when_fk_holds_instance() -> None:
    user = User(username="owner")
    password = Password.create_for_user(1, "example-password")

    password.user_id = user

    assert password.user is user


def test_non_optional_relationship_raises_when_fk_is_none() -> None:
    password = Password.create_for_user(1, "example-password")
    password.user_id = None

    with pytest.raises(AttributeError, match="required but None"):
        _ = password.user


def test_association_relationships_resolve_instances() -> None:
    user = User(username="dev")
    email = Email(email="dev@example.com")
    role = Role(name="admin")
    permission = Permission(name="repo:write", resource="repo", action="write")

    user_email = UserEmail(user_id=1, email_id=1)
    user_email.user_id = user
    user_email.email_id = email

    user_role = UserRole(user_id=1, role_id=1)
    user_role.user_id = user
    user_role.role_id = role

    user_permission = UserPermission(user_id=1, permission_id=1)
    user_permission.user_id = user
    user_permission.permission_id = permission

    role_permission = RolePermission(role_id=1, permission_id=1)
    role_permission.role_id = role
    role_permission.permission_id = permission

    configuration = Configuration(user_id=1, key="theme", value="dark")
    configuration.user_id = user

    assert user_email.user is user
    assert user_email.email is email
    assert user_role.user is user
    assert user_role.role is role
    assert user_permission.user is user
    assert user_permission.permission is permission
    assert role_permission.role is role
    assert role_permission.permission is permission
    assert configuration.user is user


def test_foreign_key_targets_are_wired_via_helper() -> None:
    assert next(iter(User.__table__.c.primary_email_id.foreign_keys)).target_fullname == "email.id"
    assert next(iter(Password.__table__.c.user_id.foreign_keys)).target_fullname == "user.id"
    assert next(iter(Configuration.__table__.c.user_id.foreign_keys)).target_fullname == "user.id"
    assert next(iter(UserEmail.__table__.c.user_id.foreign_keys)).target_fullname == "user.id"
    assert next(iter(UserEmail.__table__.c.email_id.foreign_keys)).target_fullname == "email.id"
    assert next(iter(UserPermission.__table__.c.user_id.foreign_keys)).target_fullname == "user.id"
    assert next(iter(UserPermission.__table__.c.permission_id.foreign_keys)).target_fullname == "permission.id"
    assert next(iter(UserRole.__table__.c.user_id.foreign_keys)).target_fullname == "user.id"
    assert next(iter(UserRole.__table__.c.role_id.foreign_keys)).target_fullname == "role.id"
    assert next(iter(RolePermission.__table__.c.role_id.foreign_keys)).target_fullname == "role.id"
    assert next(iter(RolePermission.__table__.c.permission_id.foreign_keys)).target_fullname == "permission.id"
