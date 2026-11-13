from __future__ import annotations

import asyncio
import gc
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel

from herogold.orm.core import loading
from herogold.orm.core.loading import AsyncLoadError, UnbatchedLoadError, build_links, link_for
from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship
from herogold.orm.testing import assert_statements, forbid_unbatched_loads

if TYPE_CHECKING:
    from pathlib import Path


class CoTeam(BaseModel, table=True):
    __tablename__ = "co_team"

    name: str = ""
    members = Relationship[list["CoPlayer"]]()
    captain = Relationship[Optional["CoPlayer"]]()


class CoPlayer(BaseModel, table=True):
    __tablename__ = "co_player"

    name: str = ""
    team = Relationship[Optional["CoTeam"]]()


class CoDesk(BaseModel, table=True):
    __tablename__ = "co_desk"

    label: str = ""
    chair = Relationship["CoPlayer"]()  # required: not Optional


build_links(CoTeam, CoPlayer)
build_links(CoDesk, CoPlayer)

def _link(session: Session, owner: BaseModel, name: str, target: BaseModel) -> None:
    info = link_for(type(owner), name)
    session.execute(insert(info.table).values(**info.owner_values(owner), **info.target_values(target)))


def _teams(session: Session, count: int, members: int = 2) -> None:
    teams = [CoTeam(name=f"team{i}") for i in range(count)]
    session.add_all(teams)
    session.flush()
    for team in teams:
        players = [CoPlayer(name=f"{team.name}-p{j}") for j in range(members)]
        session.add_all(players)
        session.flush()
        for player in players:
            _link(session, team, "members", player)
            _link(session, player, "team", team)
        _link(session, team, "captain", players[0])
    session.commit()
    session.expunge_all()


def _all_teams(session: Session) -> list[CoTeam]:
    return list(session.exec(select(CoTeam).order_by(CoTeam.id)).scalars())


def test_one_row_and_fifty_rows_cost_the_same(session: Session) -> None:
    _teams(session, 50)
    engine = session.get_bind()

    with assert_statements(engine, 2):
        teams = _all_teams(session)
        assert [p.name for p in teams[0].members] == ["team0-p0", "team0-p1"]

    session.expunge_all()
    with assert_statements(engine, 2):
        team = session.exec(select(CoTeam).where(CoTeam.name == "team7")).scalars().one()
        assert len(team.members) == 2

    session.expunge_all()
    with assert_statements(engine, 2):
        teams = _all_teams(session)
        assert all(len(t.members) == 2 for t in teams)


def test_loaded_values_are_cached_on_the_instances(session: Session) -> None:
    _teams(session, 5)
    teams = _all_teams(session)
    first = teams[0].members
    assert teams[3].captain is not None

    with assert_statements(session.get_bind(), 0):
        assert teams[0].members is first
        assert all(len(t.members) == 2 for t in teams)
        assert teams[4].captain is not None


def test_single_valued_shape_returns_object_or_none(session: Session) -> None:
    _teams(session, 3)
    session.add(CoTeam(name="lonely"))
    session.commit()
    session.expunge_all()

    teams = _all_teams(session)

    assert [t.captain.name if t.captain else None for t in teams] == ["team0-p0", "team1-p0", "team2-p0", None]


def test_required_single_relationship_without_a_linked_row_reads_as_none(session: Session) -> None:
    _teams(session, 1)
    player = session.exec(select(CoPlayer)).scalars().first()
    linked, lonely = CoDesk(label="linked"), CoDesk(label="lonely")
    session.add_all([linked, lonely])
    session.flush()
    _link(session, linked, "chair", player)
    session.commit()
    session.expunge_all()

    desks = list(session.exec(select(CoDesk).order_by(CoDesk.id)).scalars())

    assert CoDesk.chair.shape.optional is False
    assert [d.chair.name if d.chair else None for d in desks] == ["team0-p0", None]  # reading does not raise


def test_player_team_batches_through_the_loaded_members(session: Session) -> None:
    _teams(session, 10)
    teams = _all_teams(session)
    players = teams[0].members + teams[1].members

    with assert_statements(session.get_bind(), 1):
        assert [p.team.name for p in players] == ["team0", "team0", "team1", "team1"]


def test_chunks_at_the_module_constant(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _teams(session, 7)
    monkeypatch.setattr(loading, "CHUNK_SIZE", 3)

    with assert_statements(session.get_bind(), 1 + 3):  # 7 ids in chunks of 3 is 3 statements
        teams = _all_teams(session)
        assert all(len(t.members) == 2 for t in teams)


def test_chunk_size_default_is_500() -> None:
    assert loading.CHUNK_SIZE == 500


def test_detached_instance_loads_with_its_own_one_query(session: Session) -> None:
    _teams(session, 3)
    teams = _all_teams(session)
    session.expunge(teams[1])

    with assert_statements(session.get_bind(), 1):
        assert len(teams[1].members) == 2

    with assert_statements(session.get_bind(), 1):  # the rest of the cohort was not loaded by that
        assert len(teams[0].members) == 2


def test_transient_and_pending_rows_return_empty_without_a_query(session: Session) -> None:
    _teams(session, 1)
    transient = CoTeam(name="new")
    pending = CoTeam(name="pending")
    session.add(pending)

    with assert_statements(session.get_bind(), 0):
        assert transient.members == []
        assert transient.captain is None
        assert pending.members == []
        assert pending.captain is None

    assert pending.id is None  # reading did not autoflush it


def test_transient_result_is_not_cached(session: Session) -> None:
    team = CoTeam(name="t")
    assert team.members == []
    session.add(team)
    session.flush()
    player = CoPlayer(name="p")
    session.add(player)
    session.flush()
    _link(session, team, "members", player)

    assert [p.name for p in team.members] == ["p"]


def test_soft_deleted_targets_are_hidden(session: Session) -> None:
    _teams(session, 2)
    session.execute(
        CoPlayer.__table__.update().where(CoPlayer.__table__.c.name == "team0-p0").values(deleted_at=datetime.now(UTC)),
    )
    session.execute(
        CoTeam.__table__.update().where(CoTeam.__table__.c.name == "team1").values(deleted_at=datetime.now(UTC)),
    )
    session.expunge_all()
    teams = _all_teams(session)

    assert [p.name for p in teams[0].members] == ["team0-p1"]
    assert teams[0].captain is None
    players = list(session.exec(select(CoPlayer).order_by(CoPlayer.id)).scalars())
    assert players[2].team is None  # team1 is soft deleted
    assert players[0].team is teams[0] or players[0].team.name == "team0"


def test_two_result_sets_are_independent_cohorts(session: Session) -> None:
    _teams(session, 6)
    first = list(session.exec(select(CoTeam).where(CoTeam.name.in_(["team0", "team1"]))).scalars())
    second = list(session.exec(select(CoTeam).where(CoTeam.name.in_(["team4", "team5"]))).scalars())
    engine = session.get_bind()

    with assert_statements(engine, 1):
        assert len(first[0].members) == 2
        assert len(first[1].members) == 2
    with assert_statements(engine, 1):  # the first access did not load the second set
        assert len(second[0].members) == 2
        assert len(second[1].members) == 2


def test_garbage_collected_rows_leave_the_cohort(session: Session) -> None:
    _teams(session, 20)
    teams = _all_teams(session)
    keep = teams[0]
    del teams
    gc.collect()

    with assert_statements(session.get_bind(), 1):
        assert len(keep.members) == 2


def test_two_threads_load_two_result_sets(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'threads.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as seed:
        _teams(seed, 6, members=3)
    results: dict[str, list[int]] = {}
    errors: list[BaseException] = []

    def work(label: str, names: list[str]) -> None:
        try:
            with Session(engine) as own:
                rows = list(own.exec(select(CoTeam).where(CoTeam.name.in_(names)).order_by(CoTeam.id)).scalars())
                results[label] = [len(t.members) for t in rows] + [len(rows[0].members[0].team.members)]
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=work, args=("a", ["team0", "team1", "team2"])),
        threading.Thread(target=work, args=("b", ["team3", "team4", "team5"])),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert results == {"a": [3, 3, 3, 3], "b": [3, 3, 3, 3]}


def test_forbid_unbatched_loads_raises_for_a_single_row(session: Session) -> None:
    _teams(session, 3)
    one = session.exec(select(CoTeam).where(CoTeam.name == "team0")).scalars().one()
    teams = _all_teams(session)  # team0 is already loaded, so team1 and team2 form the new cohort

    with forbid_unbatched_loads():
        assert len(teams[1].members) == 2  # batched: a cohort of two
        session.expunge(teams[2])
        with pytest.raises(UnbatchedLoadError):
            _ = one.members
        with pytest.raises(UnbatchedLoadError):
            _ = teams[2].captain  # detached

    assert len(one.members) == 2  # the guard is off again


def test_plain_access_in_an_async_session_raises_with_a_hint(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _teams(session, 2)
    teams = _all_teams(session)
    monkeypatch.setattr(session.get_bind().dialect, "is_async", True)
    monkeypatch.setattr(loading, "_inside_run_sync", lambda: False)

    with pytest.raises(AsyncLoadError, match="run_sync"):
        _ = teams[0].members

    monkeypatch.setattr(loading, "_inside_run_sync", lambda: True)
    assert len(teams[0].members) == 2


def test_real_async_session_needs_run_sync_and_batches_inside_it() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as async_session:
            await async_session.run_sync(lambda sync_session: _teams(sync_session, 3))
            teams = list((await async_session.execute(select(CoTeam).order_by(CoTeam.id))).scalars())

            with pytest.raises(AsyncLoadError, match="run_sync"):
                _ = teams[0].members

            with assert_statements(engine.sync_engine, 1):
                sizes = await async_session.run_sync(lambda _sync_session: [len(team.members) for team in teams])
            assert sizes == [2, 2, 2]
        await engine.dispose()

    asyncio.run(scenario())


def test_commit_drops_cached_values(session: Session) -> None:
    _teams(session, 2)
    teams = _all_teams(session)
    assert len(teams[0].members) == 2
    extra = CoPlayer(name="extra")
    session.add(extra)
    session.flush()
    _link(session, teams[0], "members", extra)
    session.commit()

    assert len(teams[0].members) == 3


def test_refresh_drops_the_cached_value(session: Session) -> None:
    _teams(session, 1)
    team = _all_teams(session)[0]
    assert len(team.members) == 2
    extra = CoPlayer(name="extra")
    session.add(extra)
    session.flush()
    _link(session, team, "members", extra)
    session.flush()

    session.refresh(team)

    assert len(team.members) == 3


def test_expire_drops_the_cached_value(session: Session) -> None:
    _teams(session, 1)
    team = _all_teams(session)[0]
    assert len(team.members) == 2
    extra = CoPlayer(name="extra")
    session.add(extra)
    session.flush()
    _link(session, team, "members", extra)
    session.flush()

    session.expire(team)

    assert len(team.members) == 3


def test_forget_cached_drops_values_of_one_model_only(session: Session) -> None:
    _teams(session, 1)
    team = _all_teams(session)[0]
    player = session.exec(select(CoPlayer).order_by(CoPlayer.id)).scalars().first()
    assert len(team.members) == 2
    assert player is not None
    assert player.team is team

    loading.forget_cached(session, CoTeam)

    with assert_statements(session.get_bind(), 0):
        assert player.team is team
    with assert_statements(session.get_bind(), 1):
        assert len(team.members) == 2


def test_internal_write_marks_only_its_own_block() -> None:
    assert not loading.is_internal_write()
    with loading.internal_write():
        assert loading.is_internal_write()
    assert not loading.is_internal_write()
