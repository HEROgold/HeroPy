"""Query helpers on Relationship: they build statements and run nothing."""

from __future__ import annotations

import pytest
from sqlmodel import Session, select

from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship, SelfRelationship


class QAccount(BaseModel, table=True):
    name: str = "a"


class QLogin(BaseModel, table=True):
    account = Relationship(QAccount)


class QFolder(BaseModel, table=True):
    name: str = "f"
    parent = SelfRelationship()


def _accounts_and_logins(s: Session) -> tuple[list[QAccount], list[QLogin]]:
    accounts = [QAccount(name="a1"), QAccount(name="a2")]
    s.add_all(accounts)
    s.flush()
    logins = [QLogin(), QLogin(), QLogin()]
    s.add_all(logins)
    s.flush()
    QLogin.account.link(logins[0], accounts[0], session=s)
    QLogin.account.link(logins[1], accounts[0], session=s)
    QLogin.account.link(logins[2], accounts[1], session=s)
    return accounts, logins


def test_owners_of_returns_exactly_linked_owners(session: Session) -> None:
    accounts, logins = _accounts_and_logins(session)
    rows = session.exec(QLogin.account.owners_of(accounts[0])).all()
    assert {r.id for r in rows} == {logins[0].id, logins[1].id}


def test_is_set_splits_owners(session: Session) -> None:
    _accounts, logins = _accounts_and_logins(session)
    extra = QLogin()
    session.add(extra)
    session.flush()
    linked = session.exec(select(QLogin).where(QLogin.account.is_set())).all()
    unlinked = session.exec(select(QLogin).where(~QLogin.account.is_set())).all()
    assert {r.id for r in linked} == {x.id for x in logins}
    assert [r.id for r in unlinked] == [extra.id]


def test_targets_of_filtered_owners_in_one_query(session: Session) -> None:
    accounts, logins = _accounts_and_logins(session)
    query = select(QLogin).where(QLogin.id.in_([logins[0].id, logins[2].id]))  # ty: ignore[unresolved-attribute]
    rows = session.exec(QLogin.account.targets_of(query)).all()
    assert {r.id for r in rows} == {accounts[0].id, accounts[1].id}
    one = select(QLogin).where(QLogin.id == logins[1].id)  # ty: ignore[invalid-argument-type]
    assert [r.id for r in session.exec(QLogin.account.targets_of(one))] == [accounts[0].id]


def test_link_table_is_the_descriptor_table(session: Session) -> None:
    table = QLogin.account.link_table(QLogin)
    assert table is QLogin.account._links[QLogin].table
    _, logins = _accounts_and_logins(session)
    assert len(session.exec(select(table)).all()) == len(logins)


def test_nothing_executes_until_run(session: Session) -> None:
    accounts, _ = _accounts_and_logins(session)
    QLogin.account.owners_of(accounts[0])
    QLogin.account.is_set()
    QLogin.account.targets_of(select(QLogin))
    assert len(session.exec(select(QLogin.account.link_table(QLogin))).all()) == 3


def _folders(s: Session) -> tuple[QFolder, QFolder, QFolder, QFolder]:
    root, a, b, c = (QFolder(name=n) for n in ("root", "a", "b", "c"))
    s.add_all([root, a, b, c])
    s.flush()
    QFolder.parent.link(a, root, session=s)
    QFolder.parent.link(b, root, session=s)
    QFolder.parent.link(c, a, session=s)
    return root, a, b, c


def test_self_owners_of(session: Session) -> None:
    root, a, b, _ = _folders(session)
    rows = session.exec(QFolder.parent.owners_of(root)).all()
    assert {r.id for r in rows} == {a.id, b.id}


def test_self_is_set_top_level_folders(session: Session) -> None:
    root, *_ = _folders(session)
    top = session.exec(select(QFolder).where(~QFolder.parent.is_set())).all()
    assert [r.id for r in top] == [root.id]


def test_self_targets_of(session: Session) -> None:
    root, a, _, _c = _folders(session)
    owners = select(QFolder).where(QFolder.name.in_(["a", "c"]))  # ty: ignore[unresolved-attribute]
    rows = session.exec(QFolder.parent.targets_of(owners)).all()
    assert {r.id for r in rows} == {root.id, a.id}


def test_self_link_table(session: Session) -> None:
    assert QFolder.parent.link_table(QFolder) is QFolder.parent._links[QFolder].table


def test_shared_descriptor_requires_owner() -> None:
    shared = Relationship(QAccount)
    shared.__set_name__(QLogin, "shared")
    shared.build_link_for(QLogin)
    shared.build_link_for(QFolder)
    with pytest.raises(TypeError, match="owner="):
        shared.is_set()
    with pytest.raises(TypeError, match="owner="):
        shared.owners_of(QAccount())
    assert shared.link_table(QLogin) is shared._links[QLogin].table
    assert shared.is_set(owner=QLogin) is not None
