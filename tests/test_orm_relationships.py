from __future__ import annotations

from typing import TYPE_CHECKING

from herogold.orm.core.utils import get_foreign_key
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

if TYPE_CHECKING:
    from sqlmodel import Session


def test_get_foreign_key_matches_model_tablename() -> None:
    assert get_foreign_key(User) == "user.id"
    assert get_foreign_key(Email) == "email.id"
    assert get_foreign_key(Role, "name") == "role.name"


def test_optional_relationship_allows_none(session: Session) -> None:
    user = User(username="alice", primary_email_id=None)

    assert user.primary_email is None


def test_relationship_set_and_get_returns_instance(session: Session) -> None:
    user = User(username="owner")
    password = Password.create_for_user(1, "example-password")
    password.add()

    password.user = user

    assert password.user is not None
    assert password.user.id == user.id


def test_relationship_returns_none_when_unset(session: Session) -> None:
    password = Password.create_for_user(1, "example-password")
    password.add()

    assert password.user is None


def test_association_relationships_resolve_instances(session: Session) -> None:
    user = User(username="dev")
    email = Email(email="dev@example.com")
    role = Role(name="admin")
    permission = Permission(name="repo:write", resource="repo", action="write")

    user_email = UserEmail(user_id=1, email_id=1)
    user_email.add()
    user_email.user = user
    user_email.email = email

    user_role = UserRole(user_id=1, role_id=1)
    user_role.add()
    user_role.user = user
    user_role.role = role

    user_permission = UserPermission(user_id=1, permission_id=1)
    user_permission.add()
    user_permission.user = user
    user_permission.permission = permission

    role_permission = RolePermission(role_id=1, permission_id=1)
    role_permission.add()
    role_permission.role = role
    role_permission.permission = permission

    configuration = Configuration(user_id=1, key="theme", value="dark")
    configuration.add()
    configuration.user = user

    assert user_email.user is not None
    assert user_email.user.id == user.id
    assert user_email.email is not None
    assert user_email.email.id == email.id
    assert user_role.user is not None
    assert user_role.user.id == user.id
    assert user_role.role is not None
    assert user_role.role.id == role.id
    assert user_permission.user is not None
    assert user_permission.user.id == user.id
    assert user_permission.permission is not None
    assert user_permission.permission.id == permission.id
    assert role_permission.role is not None
    assert role_permission.role.id == role.id
    assert role_permission.permission is not None
    assert role_permission.permission.id == permission.id
    assert configuration.user is not None
    assert configuration.user.id == user.id


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
