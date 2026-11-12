from __future__ import annotations

import copy
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from herogold.orm import orm_session
from herogold.orm.core.configure import configure
from herogold.orm.core.model import BaseModel
from herogold.orm.core.related import RelatedList
from herogold.orm.core.utils import Relationship
from herogold.orm.testing import assert_statements, count_statements

if TYPE_CHECKING:
    from collections.abc import Iterator

POSTGRES_URL = os.environ.get("HEROPY_TEST_POSTGRES_URL")


class RlTeam(BaseModel, table=True):
    name: str = ""
    players = Relationship[list["RlPlayer"]]()


class RlPlayer(BaseModel, table=True):
    name: str = ""
    team = Relationship[Optional["RlTeam"]]()


class RlPost(BaseModel, table=True):
    title: str = ""
    tags = Relationship[list["RlTag"]]()


class RlTag(BaseModel, table=True):
    label: str = ""
    posts = Relationship[list["RlPost"]]()


configure([RlTeam, RlPlayer, RlPost, RlTag])

LINK = RlPost.tags.placement.table
TABLES = [RlTeam.__table__, RlPlayer.__table__, RlPost.__table__, RlTag.__table__, LINK]


class Db:
    def __init__(self, url: str) -> None:
        self.engine = sa.create_engine(url)

    def session(self) -> Session:
        return Session(self.engine)

    def players_of(self, name: str) -> list[str]:
        """Read straight from the table through a fresh connection, so only committed rows show."""
        query = sa.select(RlPlayer.name).join(RlTeam, RlTeam.id == RlPlayer.team_id).where(RlTeam.name == name)
        with self.engine.connect() as conn:
            return sorted(conn.execute(query.order_by(RlPlayer.name)).scalars())

    def links(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(sa.select(sa.func.count()).select_from(LINK)).scalar_one()


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=pytest.mark.skipif(not POSTGRES_URL, reason="no postgres"))])
def db(request: pytest.FixtureRequest, tmp_path: object) -> Iterator[Db]:
    database = Db(f"sqlite:///{tmp_path}/rl.db" if request.param == "sqlite" else str(POSTGRES_URL))
    BaseModel.metadata.drop_all(database.engine, tables=TABLES)
    BaseModel.metadata.create_all(database.engine, tables=TABLES)
    yield database
    BaseModel.metadata.drop_all(database.engine, tables=TABLES)
    database.engine.dispose()


def _count(session: Session, table: sa.Table) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def _seed(db: Db) -> None:
    with db.session() as s:
        s.add_all([RlTeam(name="red"), RlTeam(name="blue")])
        s.add_all(RlTag(label=f"t{i}") for i in range(5))
        s.add_all(RlPost(title=f"p{i}") for i in range(3))
        s.commit()


def _one[T](session: Session, model: type[T], **where: object) -> T:
    return session.execute(sa.select(model).filter_by(**where)).scalar_one()


# ---- foreign-key one-to-many ----


def test_fk_list_is_a_related_list_and_append_writes_after_flush(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        assert isinstance(red.players, RelatedList)
        assert red.players == []
        player = RlPlayer(name="ann")
        red.players.append(player)
        assert red.players == [player]
        assert player.team is red
        s.flush()
        assert player.team_id == red.id
        assert _count(s, RlPlayer.__table__) == 1
        assert db.players_of("red") == []  # not committed yet
        s.commit()
    assert db.players_of("red") == ["ann"]


def test_fk_extend_remove_clear(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        players = [RlPlayer(name=n) for n in "abc"]
        red.players.extend(players)
        s.commit()
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        assert sorted(p.name for p in red.players) == ["a", "b", "c"]
        red.players.remove(next(p for p in red.players if p.name == "b"))
        assert sorted(p.name for p in red.players) == ["a", "c"]
        s.flush()
        s.commit()
    assert db.players_of("red") == ["a", "c"]
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        red.players.clear()
        assert red.players == []
        s.commit()
    assert db.players_of("red") == []
    with db.session() as s:
        assert _count(s, RlPlayer.__table__) == 3  # unlinked, not deleted


def test_fk_append_moves_a_player_between_teams_and_both_lists_refresh(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red, blue = _one(s, RlTeam, name="red"), _one(s, RlTeam, name="blue")
        player = RlPlayer(name="ann")
        red.players.append(player)
        s.flush()
        assert red.players == [player]
        assert blue.players == []
        blue.players.append(player)
        assert red.players == []
        assert blue.players == [player]
        assert player.team is blue
        s.commit()
    assert db.players_of("red") == []
    assert db.players_of("blue") == ["ann"]


def test_appending_the_same_item_twice_keeps_one_entry(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        player = RlPlayer(name="ann")
        red.players.append(player)
        red.players.append(player)
        assert red.players == [player]


# ---- assigning single-valued relationships ----


def test_assigning_a_single_relationship_sets_the_column_and_syncs_the_inverse(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red, blue = _one(s, RlTeam, name="red"), _one(s, RlTeam, name="blue")
        player = RlPlayer(name="ann")
        s.add(player)
        assert red.players == []  # both lists are cached now
        assert blue.players == []
        player.team = red
        assert player.team is red
        assert red.players == [player]
        s.flush()
        assert player.team_id == red.id
        player.team = blue
        assert red.players == []
        assert blue.players == [player]
        s.flush()
        assert player.team_id == blue.id
        player.team = None
        assert player.team is None
        assert blue.players == []
        s.flush()
        assert player.team_id is None
        player.team = red
        s.commit()
    assert db.players_of("red") == ["ann"]


def test_assigning_to_a_list_raises(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        with pytest.raises(TypeError):
            red.players = [RlPlayer(name="x")]


def test_a_row_outside_any_session_raises_on_write() -> None:
    team = RlTeam(name="loose")
    with pytest.raises(RuntimeError):
        team.players.append(RlPlayer(name="x"))
    with pytest.raises(RuntimeError):
        RlPlayer(name="y").team = team


# ---- link-table many-to-many ----


def test_link_list_append_extend_remove_clear(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        tags = list(s.execute(sa.select(RlTag).order_by(RlTag.id)).scalars())
        assert isinstance(post.tags, RelatedList)
        post.tags.append(tags[0])
        post.tags.extend(tags[1:3])
        assert post.tags == tags[:3]
        s.flush()  # a session with nothing else to write does not flush; the next read does
        assert [t.posts for t in tags[:3]] == [[post]] * 3  # read from the table
        assert db.links() == 0  # not committed
        post.tags.remove(tags[1])
        assert post.tags == [tags[0], tags[2]]
        assert tags[1].posts == []
        s.commit()
    assert db.links() == 2
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        assert sorted(t.label for t in post.tags) == ["t0", "t2"]
        post.tags.clear()
        assert post.tags == []
        s.commit()
    assert db.links() == 0


def test_link_inverse_lists_stay_in_sync(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post, tag = _one(s, RlPost, title="p0"), _one(s, RlTag, label="t0")
        assert tag.posts == []
        post.tags.append(tag)
        assert tag.posts == [post]
        post.tags.remove(tag)
        assert tag.posts == []
        tag.posts.append(post)
        assert post.tags == [tag]
        s.commit()
    assert db.links() == 1


def test_link_writes_apply_on_commit_of_a_clean_session(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        tag = _one(s, RlTag, label="t0")
        s.commit()
        post.tags.append(tag)  # both rows exist: nothing else is dirty
        assert db.links() == 0
        s.commit()
    assert db.links() == 1


def test_a_read_applies_queued_link_writes(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post, tag = _one(s, RlPost, title="p0"), _one(s, RlTag, label="t0")
        post.tags.append(tag)  # the inverse list of tag is not loaded, so it cannot be updated in memory
        assert tag.posts == [post]  # the read applies the queued link first
        assert s.in_transaction()
        s.rollback()
    assert db.links() == 0


def test_never_flushed_owner_and_targets_queue_until_they_have_ids(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        existing = _one(s, RlTag, label="t0")
        post = RlPost(title="new")
        s.add(post)
        fresh = RlTag(label="fresh")
        post.tags.extend([existing, fresh])
        assert post.id is None
        s.flush()  # one flush writes the rows and the links
        assert _count(s, LINK) == 2
        assert s.in_transaction()
        s.commit()
    assert db.links() == 2
    with db.session() as s:
        assert sorted(t.label for t in _one(s, RlPost, title="new").tags) == ["fresh", "t0"]


def test_never_flushed_owner_with_fk_children_writes_in_one_flush(db: Db) -> None:
    with db.session() as s:
        team = RlTeam(name="green")
        s.add(team)
        team.players.extend([RlPlayer(name="a"), RlPlayer(name="b")])
        s.flush()
        assert {p.team_id for p in team.players} == {team.id}
        assert not s.dirty
        s.commit()
    assert db.players_of("green") == ["a", "b"]


def test_never_flushed_owner_gets_its_links_on_commit_without_a_flush(db: Db) -> None:
    with db.session() as s:
        post = RlPost(title="x")
        s.add(post)
        post.tags.append(RlTag(label="y"))
        s.commit()
    assert db.links() == 1


# ---- transactions ----


def test_rollback_leaves_nothing(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        post = _one(s, RlPost, title="p0")
        red.players.append(RlPlayer(name="ann"))
        post.tags.append(RlTag(label="new"))
        s.flush()
        post.tags.append(_one(s, RlTag, label="t1"))
        s.rollback()
        assert red.players == []
        assert post.tags == []
        s.commit()
    assert db.players_of("red") == []
    assert db.links() == 0


def test_rollback_drops_writes_that_were_still_queued(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post, tag = _one(s, RlPost, title="p0"), _one(s, RlTag, label="t0")
        post.tags.append(tag)
        s.rollback()
        s.commit()  # a queued write that survived would run here
    assert db.links() == 0


def test_the_orm_never_commits(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red, post = _one(s, RlTeam, name="red"), _one(s, RlPost, title="p0")
        red.players.append(RlPlayer(name="ann"))
        post.tags.append(_one(s, RlTag, label="t0"))
        post.tags.remove(post.tags[0])
        post.tags.append(_one(s, RlTag, label="t1"))
        red.players.clear()
        s.flush()
        assert s.in_transaction()
        assert db.players_of("red") == []
        assert db.links() == 0
        s.rollback()
    assert db.links() == 0


# ---- statements ----


def test_appending_n_link_items_writes_the_links_in_one_statement(db: Db) -> None:
    with db.session() as s:
        posts = [RlPost(title="a"), RlPost(title="b")]
        s.add_all(posts)
        s.flush()
        for post in posts:
            _ = post.tags  # load the lists before counting
        for post, n in zip(posts, (3, 30), strict=True):
            with count_statements(db.engine) as counter:
                post.tags.extend(RlTag(label=f"x{i}") for i in range(n))
                s.flush()
            link_writes = [x for x in counter.statements if "rlpost_tags" in x]
            assert len(link_writes) == 1, counter.statements
            assert [x for x in counter.statements if x.lstrip().upper().startswith("UPDATE")] == []
        s.rollback()


def test_appending_n_fk_items_to_a_stored_owner_writes_no_extra_statement(db: Db) -> None:
    with db.session() as s:
        teams = [RlTeam(name="a"), RlTeam(name="b")]
        s.add_all(teams)
        s.flush()
        for team in teams:
            _ = team.players
        for team, n in zip(teams, (3, 30), strict=True):
            with count_statements(db.engine) as counter:
                team.players.extend(RlPlayer(name=f"x{i}") for i in range(n))
                s.flush()
            # the foreign key is set before the insert, so the rows are written once
            assert all(x.lstrip().upper().startswith("INSERT") for x in counter.statements), counter.statements
        s.rollback()


def test_new_owner_with_new_items_updates_the_keys_in_one_statement(db: Db) -> None:
    with db.session() as s:
        for n in (3, 30):
            team = RlTeam(name=f"t{n}")
            s.add(team)
            with count_statements(db.engine) as counter:
                team.players.extend(RlPlayer(name=f"x{i}") for i in range(n))
                s.flush()
            updates = [x for x in counter.statements if x.lstrip().upper().startswith("UPDATE")]
            assert len(updates) == 1, counter.statements
            assert not s.dirty
        s.rollback()


def test_link_append_to_existing_rows_is_one_statement(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        tags = list(s.execute(sa.select(RlTag)).scalars())
        _ = post.tags
        with assert_statements(db.engine, 1):
            post.tags.extend(tags)
            s.commit()
    assert db.links() == 5


# ---- list behaviour ----


def test_list_methods_beyond_the_writes(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        tags = list(s.execute(sa.select(RlTag).order_by(RlTag.id)).scalars())
        post.tags += tags[:2]
        assert post.tags == tags[:2]
        assert post.tags.pop() is tags[1]
        assert post.tags == tags[:1]
        del post.tags[0]
        assert post.tags == []
        with pytest.raises(TypeError):
            post.tags.insert(0, tags[0])
        with pytest.raises(TypeError):
            post.tags[0:0] = [tags[0]]
        with pytest.raises(ValueError):  # noqa: PT011
            post.tags.remove(tags[3])
        s.flush()
        s.commit()
    assert db.links() == 0


# ---- soft delete ----


def test_soft_deleted_targets_stay_hidden(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        post = _one(s, RlPost, title="p0")
        a, b = RlPlayer(name="a"), RlPlayer(name="b")
        red.players.extend([a, b])
        post.tags.extend([_one(s, RlTag, label="t0"), _one(s, RlTag, label="t1")])
        s.commit()
        a.deleted_at = datetime.now(UTC)
        _one(s, RlTag, label="t0").deleted_at = datetime.now(UTC)
        s.commit()
        assert [p.name for p in red.players] == ["b"]
        assert [t.label for t in post.tags] == ["t1"]


class SavepointRefused(Exception):  # noqa: N818
    pass


def test_savepoint_rollback_drops_queued_link_writes_and_cached_lists(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        failed, kept = _one(s, RlTag, label="t0"), _one(s, RlTag, label="t1")
        assert post.tags == []
        nested = s.begin_nested()
        post.tags.append(failed)
        nested.rollback()

        assert post.tags == []
        post.tags.append(kept)
        s.commit()
    assert db.links() == 1
    with db.session() as s:
        assert [t.label for t in _one(s, RlPost, title="p0").tags] == ["t1"]


def test_savepoint_rollback_keeps_writes_queued_before_it(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        early, failed = _one(s, RlTag, label="t0"), _one(s, RlTag, label="t1")
        post.tags.append(early)
        nested = s.begin_nested()
        post.tags.append(failed)
        nested.rollback()
        s.commit()
    with db.session() as s:
        assert [t.label for t in _one(s, RlPost, title="p0").tags] == ["t0"]


def test_savepoint_rollback_undoes_a_foreign_key_append(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        ann = RlPlayer(name="ann")
        s.add(ann)
        s.flush()
        assert red.players == []
        nested = s.begin_nested()
        red.players.append(ann)
        nested.rollback()

        assert red.players == []
        assert ann.team is None
        s.commit()
    assert db.players_of("red") == []


def _append_then_fail(db: Db, post: RlPost, tag: RlTag) -> None:
    with orm_session(db.engine):
        post.tags.append(tag)
        raise SavepointRefused


def test_failed_joined_scope_block_leaves_no_link_row(db: Db) -> None:
    _seed(db)
    with orm_session(db.engine) as s:
        post, tag = _one(s, RlPost, title="p0"), _one(s, RlTag, label="t0")
        with pytest.raises(SavepointRefused):
            _append_then_fail(db, post, tag)
        assert post.tags == []
    assert db.links() == 0


def test_deleting_a_single_valued_relationship_clears_it(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        ann = RlPlayer(name="ann")
        red.players.append(ann)
        s.flush()
        assert ann.team is red

        del ann.team

        assert ann.team is None
        assert red.players == []
        s.commit()
    assert db.players_of("red") == []


def test_deleting_a_many_valued_relationship_raises(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        with pytest.raises(TypeError, match="many-valued"):
            del red.players


# ---- every mutator writes through, or refuses ----


def test_pop_unrelates_and_returns_the_item(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        tags = list(s.execute(sa.select(RlTag).order_by(RlTag.id)).scalars())
        post.tags.extend(tags[:3])
        assert post.tags.pop(0) is tags[0]
        assert post.tags.pop() is tags[2]
        assert post.tags == [tags[1]]
        s.flush()
        _ = tags[3].posts  # a typed read applies the queued link writes
        assert _count(s, LINK) == 1
        with pytest.raises(IndexError):
            post.tags.pop(5)
        s.commit()
    assert db.links() == 1


def test_del_by_index_and_by_slice_unrelate_the_items(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        tags = list(s.execute(sa.select(RlTag).order_by(RlTag.id)).scalars())
        post.tags.extend(tags)
        del post.tags[0]
        assert post.tags == tags[1:]
        del post.tags[1:3]
        assert post.tags == [tags[1], tags[4]]
        s.flush()
        _ = tags[3].posts  # a typed read applies the queued link writes
        assert _count(s, LINK) == 2
        assert tags[2].posts == []
        s.commit()
    assert db.links() == 2


def test_del_by_index_on_a_foreign_key_list_clears_the_column(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        ann, bob = RlPlayer(name="ann"), RlPlayer(name="bob")
        red.players.extend([ann, bob])
        s.flush()
        del red.players[0]
        s.commit()
    assert db.players_of("red") == ["bob"]


def test_iadd_writes_through_and_rollback_leaves_nothing(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        tags = list(s.execute(sa.select(RlTag).order_by(RlTag.id)).scalars())
        before = post.tags
        post.tags += tags[:2]
        assert post.tags is before  # += keeps the same RelatedList
        assert isinstance(post.tags, RelatedList)
        s.flush()
        _ = tags[3].posts  # a typed read applies the queued link writes
        assert _count(s, LINK) == 2  # visible after the flush, in this transaction
        assert db.links() == 0  # not committed
        s.rollback()
        assert post.tags == []
    assert db.links() == 0


def test_iadd_on_a_foreign_key_list_commits(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        red = _one(s, RlTeam, name="red")
        red.players += [RlPlayer(name="ann"), RlPlayer(name="bob")]
        s.commit()
    assert db.players_of("red") == ["ann", "bob"]


def test_insert_item_assignment_and_whole_list_assignment_raise(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post = _one(s, RlPost, title="p0")
        red = _one(s, RlTeam, name="red")
        tag = _one(s, RlTag, label="t0")
        post.tags.append(tag)
        with pytest.raises(TypeError, match="no stored order"):
            post.tags.insert(0, tag)
        with pytest.raises(TypeError, match="cannot replace"):
            post.tags[0] = _one(s, RlTag, label="t1")
        with pytest.raises(TypeError):
            post.tags = [tag]
        with pytest.raises(TypeError):
            red.players = [RlPlayer(name="x")]
        assert post.tags == [tag]  # nothing changed


# ---- when a link-only change is applied ----


def test_a_link_only_change_is_not_applied_by_flush_but_by_a_typed_read_or_commit(db: Db) -> None:
    _seed(db)
    with db.session() as s:
        post, tag = _one(s, RlPost, title="p0"), _one(s, RlTag, label="t0")
        red = _one(s, RlTeam, name="red")
        s.commit()  # a clean session: no row is dirty
        post.tags.append(tag)

        s.flush()
        assert _count(s, LINK) == 0  # flush has nothing dirty to write, so the link stays queued

        assert red.players == []  # a read of any typed relationship on the session applies the queue
        assert _count(s, LINK) == 1
        s.rollback()

        post.tags.append(tag)
        s.commit()  # commit applies it too
    assert db.links() == 1


# ---- copies ----


def test_copying_a_link_list_queues_no_writes_and_breaks_no_constraint(db: Db) -> None:
    with db.session() as s:
        post = RlPost(title="a")
        s.add(post)
        s.flush()
        post.tags.extend([RlTag(label="x"), RlTag(label="y")])
        s.commit()
        tags = post.tags
        assert isinstance(tags, RelatedList)

        with count_statements(db.engine) as counter:
            shallow = copy.copy(tags)
            deep = copy.deepcopy(tags)
            s.commit()  # a replayed append would insert the same link rows again and violate the key

        assert type(shallow) is list
        assert type(deep) is list
        assert [t.label for t in shallow] == ["x", "y"]
        assert [t.label for t in deep] == ["x", "y"]
        assert [x for x in counter.statements if "rlpost_tags" in x and "INSERT" in x.upper()] == []
        assert db.links() == 2


def test_copying_an_fk_list_does_not_change_the_rows(db: Db) -> None:
    with db.session() as s:
        team = RlTeam(name="t")
        s.add(team)
        s.flush()
        team.players.append(RlPlayer(name="p"))
        s.commit()

        clone = copy.copy(team.players)
        clone.append(RlPlayer(name="q"))  # a plain list: no write reaches the session
        s.commit()

    assert db.players_of("t") == ["p"]

