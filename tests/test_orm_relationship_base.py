from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union  # noqa: UP035

import pytest
from sqlmodel import SQLModel

from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import SELF, Relationship, Shape, _shape_of

if TYPE_CHECKING:
    from sqlmodel import Session


class RbTeam(BaseModel, table=True):
    __tablename__ = "rb_team"

    name: str = ""
    members = Relationship[list["RbPlayer"]]()
    captain = Relationship[Optional["RbPlayer"]]()


class RbPlayer(BaseModel, table=True):
    __tablename__ = "rb_player"

    name: str = ""
    team = Relationship[Optional["RbTeam"]]()
    home = Relationship["RbTeam"]()
    club = Relationship["RbTeam | None"]()
    union_team = Relationship[Union["RbTeam", None]]()


def test_list_type_argument_is_many_valued_and_required() -> None:
    assert RbTeam.__dict__["members"].shape == Shape(many=True, optional=False)


def test_optional_type_argument_is_single_valued_and_optional() -> None:
    assert RbPlayer.__dict__["team"].shape == Shape(many=False, optional=True)
    assert RbPlayer.__dict__["union_team"].shape == Shape(many=False, optional=True)
    assert RbTeam.__dict__["captain"].shape == Shape(many=False, optional=True)


def test_bare_type_argument_is_single_valued_and_required() -> None:
    assert RbPlayer.__dict__["home"].shape == Shape(many=False, optional=False)


def test_quoted_union_type_argument_is_optional() -> None:
    assert RbPlayer.__dict__["club"].shape == Shape(many=False, optional=True)


def test_forward_references_resolve_after_all_models_exist() -> None:
    assert RbTeam.__dict__["members"].resolve() is RbPlayer
    assert RbTeam.__dict__["captain"].resolve() is RbPlayer
    assert RbPlayer.__dict__["team"].resolve() is RbTeam
    assert RbPlayer.__dict__["home"].resolve() is RbTeam
    assert RbPlayer.__dict__["club"].resolve() is RbTeam


def test_resolve_is_not_needed_at_class_creation() -> None:
    class RbEarly(BaseModel, table=True):
        __tablename__ = "rb_early"

        later = Relationship[list["RbNeverDefined"]]()  # noqa: F821

    descriptor = RbEarly.__dict__["later"]
    assert descriptor.shape == Shape(many=True, optional=False)
    with pytest.raises(NameError):
        descriptor.resolve()


def test_unannotated_relationship_creates_no_column() -> None:
    assert set(RbTeam.__table__.c.keys()) == {"id", "created_at", "updated_at", "deleted_at"} | {"name"}
    assert "members" not in RbTeam.__table__.c
    assert "team" not in RbPlayer.__table__.c
    assert "team_id" not in RbPlayer.__table__.c
    assert "members" not in RbTeam.model_fields
    assert "team" not in RbPlayer.model_fields
    assert "rb_team_members" not in SQLModel.metadata.tables


def test_new_form_does_not_build_a_link_table() -> None:
    assert "rb_player_team" not in SQLModel.metadata.tables


def test_old_call_form_still_works() -> None:
    old = Relationship(RbTeam)

    assert old.related_model is RbTeam
    assert old.optional is True
    assert Relationship().related_model is SELF


def test_old_call_form_has_no_declared_shape() -> None:
    assert Relationship(RbTeam).shape == Shape(many=False, optional=True)
    assert Relationship(RbTeam, optional=False).shape == Shape(many=False, optional=False)


def test_new_form_instance_access_before_configure_warns_and_raises(session: Session) -> None:
    player = RbPlayer(name="p")

    with pytest.warns(UserWarning, match="configure"), pytest.raises(RuntimeError, match="configure"):
        player.team  # noqa: B018


def test_new_form_class_access_returns_the_descriptor() -> None:
    assert RbTeam.members is RbTeam.__dict__["members"]


class RbDel(BaseModel, table=True):
    __tablename__ = "rb_del"

    many = Relationship[list["RbPlayer"]]()
    one = Relationship[Optional["RbPlayer"]]()


@pytest.mark.parametrize(
    ("quoted", "unquoted", "expected"),
    [
        ("Optional[RbTeam]", Optional[RbTeam], Shape(many=False, optional=True)),  # noqa: UP045
        ("Union[RbTeam, None]", Union[RbTeam, None], Shape(many=False, optional=True)),  # noqa: UP007
        ("Union[None, RbTeam]", Union[None, RbTeam], Shape(many=False, optional=True)),  # noqa: UP007
        ("typing.Optional[RbTeam]", Optional[RbTeam], Shape(many=False, optional=True)),  # noqa: UP045
        ("List[RbPlayer]", List[RbPlayer], Shape(many=True, optional=False)),  # noqa: UP006
        ("typing.List[RbPlayer]", List[RbPlayer], Shape(many=True, optional=False)),  # noqa: UP006
        ("list[RbPlayer]", list[RbPlayer], Shape(many=True, optional=False)),
        ("Optional[List[RbPlayer]]", Optional[List[RbPlayer]], Shape(many=True, optional=True)),  # noqa: UP045, UP006
        ("RbTeam | None", RbTeam | None, Shape(many=False, optional=True)),
        ("RbTeam", RbTeam, Shape(many=False, optional=False)),
    ],
)
def test_quoted_and_unquoted_type_arguments_give_the_same_shape(quoted: str, unquoted: object, expected: Shape) -> None:
    assert _shape_of(quoted) == expected
    assert _shape_of(unquoted) == expected


def test_quoted_union_of_two_types_is_rejected() -> None:
    with pytest.raises(TypeError):
        _shape_of("Union[RbTeam, RbPlayer]")


def test_deleting_a_list_relationship_raises_type_error() -> None:
    with pytest.raises(TypeError, match="many"):
        del RbDel().many
