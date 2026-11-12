"""Type-checker example for ``Relationship[T]()``; ``ty`` and ``pyrefly`` must both accept it.

Run it with ``uv run --with ty ty check tests/typecheck`` and ``uvx pyrefly@1.3.1 check tests/typecheck``.
This is not a pytest module. Each ``assert_type`` pins an inferred type, and each
``ignore`` comment marks a line that must be an error.
"""

# ruff: noqa: UP045, B018
from __future__ import annotations

from typing import Optional, assert_type

from herogold.orm.core.model import _BaseModel
from herogold.orm.core.utils import Relationship


class Team:
    name: str
    members = Relationship[list["Player"]]()
    captain = Relationship[Optional["Player"]]()


class Player:
    name: str
    team = Relationship[Optional[Team]]()
    home = Relationship[Team]()


def instance_access(team: Team, player: Player) -> None:
    assert_type(team.members, list[Player])
    assert_type(team.captain, Optional[Player])
    assert_type(player.team, Optional[Team])
    assert_type(player.home, Team)


def class_access() -> None:
    assert_type(Team.members, Relationship[list[Player]])
    assert_type(Player.team, Relationship[Optional[Team]])


def prefetch(*relationships: Relationship[object]) -> None: ...


def wrong_use(team: Team) -> None:
    Team.memberz  # ty: ignore[missing-attribute]  # pyrefly: ignore [missing-attribute]
    team.members = 3  # ty: ignore[invalid-assignment]  # pyrefly: ignore [bad-argument-type]


class Pet(_BaseModel):
    """Target of the original call form."""


class Owner:
    """The original form ``Relationship(Target)`` keeps ``Target | None`` and ``type[Target]``."""

    pet = Relationship(Pet)
    typed_pet = Relationship[Pet]()


def legacy_form(owner: Owner) -> None:
    assert_type(owner.pet, Pet | None)
    assert_type(Owner.pet, type[Pet])


def new_form(owner: Owner) -> None:
    assert_type(owner.typed_pet, Pet)
    assert_type(Owner.typed_pet, Relationship[Pet])
