from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select, update
from sqlalchemy.orm.attributes import set_attribute

from herogold.orm.core import loading
from herogold.orm.core.configure import configure
from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship
from herogold.orm.testing import assert_statements

if TYPE_CHECKING:
    from sqlmodel import Session


class FkAuthor(BaseModel, table=True):
    name: str = ""
    books = Relationship[list["FkBook"]]()


class FkBook(BaseModel, table=True):
    title: str = ""
    author = Relationship[Optional["FkAuthor"]]()


class FkTag(BaseModel, table=True):
    label: str = ""
    posts = Relationship[list["FkPost"]]()


class FkPost(BaseModel, table=True):
    title: str = ""
    tags = Relationship[list["FkTag"]]()


configure([FkAuthor, FkBook, FkTag, FkPost])


def _seed(session: Session, authors: int, books: int = 2) -> None:
    rows = [FkAuthor(name=f"a{i}") for i in range(authors)]
    session.add_all(rows)
    session.flush()
    session.add_all(FkBook(title=f"a{i}-b{j}", author_id=author.id) for i, author in enumerate(rows) for j in range(books))
    session.commit()
    session.expunge_all()


def test_many_to_one_costs_the_same_for_one_row_and_fifty(session: Session) -> None:
    _seed(session, 50)
    engine = session.get_bind()
    one = session.execute(select(FkBook).where(FkBook.title == "a7-b0")).scalars().all()
    with assert_statements(engine, 1):
        assert [b.author.name for b in one] == ["a7"]

    session.expunge_all()
    with assert_statements(engine, 2):  # the books, then every author at once
        books = list(session.execute(select(FkBook)).scalars())
        assert len(books) == 100
        assert all(b.author is not None and b.title.startswith(b.author.name) for b in books)


def test_one_to_many_costs_the_same_for_one_row_and_fifty(session: Session) -> None:
    _seed(session, 50)
    engine = session.get_bind()
    one = session.execute(select(FkAuthor).where(FkAuthor.name == "a7")).scalars().all()
    with assert_statements(engine, 1):
        assert [[b.title for b in a.books] for a in one] == [["a7-b0", "a7-b1"]]

    session.expunge_all()
    with assert_statements(engine, 2):  # the authors, then every book at once
        authors = list(session.execute(select(FkAuthor)).scalars())
        assert len(authors) == 50
        assert all(len(a.books) == 2 for a in authors)


def test_soft_deleted_targets_are_hidden(session: Session) -> None:
    _seed(session, 2)
    now = datetime.now(UTC)
    session.execute(update(FkBook).where(FkBook.title == "a0-b0").values(deleted_at=now))
    session.execute(update(FkAuthor).where(FkAuthor.name == "a1").values(deleted_at=now))
    session.expunge_all()

    authors = list(session.execute(select(FkAuthor).where(FkAuthor.name == "a0")).scalars())
    books = list(session.execute(select(FkBook).order_by(FkBook.id)).scalars())

    assert [b.title for b in authors[0].books] == ["a0-b1"]
    assert books[2].author is None  # a1 is soft deleted
    assert books[1].author is not None


def test_never_flushed_and_detached_rows(session: Session) -> None:
    _seed(session, 3)
    engine = session.get_bind()
    fresh = FkAuthor(name="new")
    with assert_statements(engine, 0):
        assert fresh.books == []
        assert FkBook(title="x").author is None

    authors = list(session.execute(select(FkAuthor).order_by(FkAuthor.id)).scalars())
    session.expunge(authors[1])
    with assert_statements(engine, 1):
        assert len(authors[1].books) == 2


def test_many_to_one_reads_foreign_keys_set_in_the_session(session: Session) -> None:
    _seed(session, 2)
    books = list(session.execute(select(FkBook).order_by(FkBook.id)).scalars())
    authors = list(session.execute(select(FkAuthor).order_by(FkAuthor.id)).scalars())
    set_attribute(books[0], "author_id", authors[1].id)

    assert books[0].author is authors[1]


def test_link_table_relationships_load_in_one_query(session: Session) -> None:
    tags = [FkTag(label=f"t{i}") for i in range(3)]
    posts = [FkPost(title=f"p{i}") for i in range(20)]
    session.add_all([*tags, *posts])
    session.flush()
    placement = FkPost.tags.placement
    session.execute(placement.table.insert(), [{placement.near: p.id, placement.far: t.id} for p in posts for t in tags])
    session.commit()
    session.expunge_all()

    with assert_statements(session.get_bind(), 2):
        loaded = list(session.execute(select(FkPost)).scalars())
        assert all(len(p.tags) == 3 for p in loaded)


def test_writing_the_fk_column_drops_the_cached_many_to_one(session: Session) -> None:
    _seed(session, 2)
    books = list(session.execute(select(FkBook).order_by(FkBook.id)).scalars())
    authors = list(session.execute(select(FkAuthor).order_by(FkAuthor.id)).scalars())
    assert books[0].author is authors[0]

    set_attribute(books[0], "author_id", authors[1].id)

    assert books[0].author is authors[1]
    set_attribute(books[0], "author_id", None)
    assert books[0].author is None


def test_writing_the_fk_column_drops_the_cached_list_of_both_authors(session: Session) -> None:
    _seed(session, 2)
    books = list(session.execute(select(FkBook).order_by(FkBook.id)).scalars())
    authors = list(session.execute(select(FkAuthor).order_by(FkAuthor.id)).scalars())
    assert [len(a.books) for a in authors] == [2, 2]
    moved = books[0]

    set_attribute(moved, "author_id", authors[1].id)
    session.flush()

    assert [len(a.books) for a in authors] == [1, 3]


def test_refresh_and_expire_drop_the_cached_fk_relationship(session: Session) -> None:
    _seed(session, 2)
    books = list(session.execute(select(FkBook).order_by(FkBook.id)).scalars())
    authors = list(session.execute(select(FkAuthor).order_by(FkAuthor.id)).scalars())
    assert books[0].author is authors[0]
    session.execute(update(FkBook).where(FkBook.id == books[0].id).values(author_id=authors[1].id))

    session.refresh(books[0])
    assert books[0].author is authors[1]

    session.execute(update(FkBook).where(FkBook.id == books[0].id).values(author_id=authors[0].id))
    session.expire(books[0])
    assert books[0].author is authors[0]


def test_column_writes_inside_internal_write_keep_the_cache(session: Session) -> None:
    _seed(session, 2)
    books = list(session.execute(select(FkBook).order_by(FkBook.id)).scalars())
    authors = list(session.execute(select(FkAuthor).order_by(FkAuthor.id)).scalars())
    assert books[0].author is authors[0]

    with loading.internal_write():
        set_attribute(books[0], "author_id", authors[1].id)

    assert books[0].author is authors[0]
