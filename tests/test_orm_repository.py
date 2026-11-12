from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, ClassVar, Optional

import pytest

from herogold.orm import QuerySet, Repository, Upserted
from herogold.orm.core import loading
from herogold.orm.core.configure import configure
from herogold.orm.core.model import Actions, BaseModel, DataModel
from herogold.orm.core.utils import Relationship
from herogold.orm.testing import assert_statements, count_statements

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlmodel import Session


class RepoSale(BaseModel, table=True):
    title: str = ""
    percent: int = 0


class RepoTag(BaseModel, table=True):
    owner: str = ""
    label: str = ""
    weight: int = 0
    natural_key: ClassVar[tuple[str, ...]] = ("owner", "label")


class RepoTenant(BaseModel, table=True):
    name: str = ""
    tenant: int = 1

    @classmethod
    def default_criteria(cls) -> list[ColumnElement[bool]]:
        return [*super().default_criteria(), cls.tenant == 1]


class Sales(Repository[RepoSale]):
    pass


def _seed(session: Session, total: int = 50, deleted: int = 5) -> Sales:
    sales = Sales(session)
    sales.add_all(RepoSale(id=i, title=f"s{i}", percent=10) for i in range(1, total + 1))
    session.flush()
    sales.qs().where(RepoSale.id <= deleted).soft_delete()
    session.flush()
    return sales


def test_model_from_subclass_and_from_generic_alias(session: Session) -> None:
    assert Sales(session).model is RepoSale
    assert Repository[RepoTag](session).model is RepoTag


def test_repository_never_commits(session: Session) -> None:
    sales = Sales(session)
    sales.add(RepoSale(id=1))
    session.flush()
    session.rollback()

    assert sales.qs().count() == 0


def test_count_contains_getitem(session: Session) -> None:
    sales = _seed(session)

    assert sales.qs().count() == 45
    assert 7 in sales
    assert 3 not in sales
    assert sales[7] in sales
    assert sales[7].id == 7


def test_getitem_missing_or_deleted_raises_keyerror(session: Session) -> None:
    sales = _seed(session)

    with pytest.raises(KeyError):
        sales[3]
    with pytest.raises(KeyError):
        sales[999]


def test_repository_slice_is_refused(session: Session) -> None:
    sales = _seed(session)

    with pytest.raises(TypeError):
        sales[1:3]


def test_bool_is_one_exists_statement(session: Session) -> None:
    sales = _seed(session)
    engine = session.get_bind()

    with assert_statements(engine, 1) as counter:
        assert bool(sales)
    assert "EXISTS" in counter.statements[0].upper()
    assert "COUNT" not in counter.statements[0].upper()


def test_bool_false_on_empty(session: Session) -> None:
    assert not Sales(session)


def test_iteration_yields_alive_rows(session: Session) -> None:
    sales = _seed(session)

    assert sum(1 for _ in sales) == 45


def test_delitem_soft_deletes_and_missing_raises(session: Session) -> None:
    sales = _seed(session)

    del sales[7]

    assert 7 not in sales
    assert 7 in sales.qs().with_deleted()
    with pytest.raises(KeyError):
        del sales[7]


def test_delete_soft_deletes_and_purge_hard_deletes(session: Session) -> None:
    sales = _seed(session)
    row = sales[10]

    sales.delete(row)
    session.flush()
    assert row.deleted_at is not None
    assert 10 in sales.qs().with_deleted()

    sales.purge(row)
    session.flush()
    assert 10 not in sales.qs().with_deleted()


def test_queryset_is_immutable(session: Session) -> None:
    sales = _seed(session)
    base = sales.qs()
    narrowed = base.where(RepoSale.id < 0)

    assert narrowed is not base
    assert narrowed.count() == 0
    assert base.count() == 45


def test_deleted_visibility(session: Session) -> None:
    sales = _seed(session)

    assert sales.qs().count() == 45
    assert sales.qs().with_deleted().count() == 50
    assert sorted(row.id for row in sales.qs().only_deleted()) == [1, 2, 3, 4, 5]


def test_with_deleted_keeps_other_default_criteria(session: Session) -> None:
    repo = Repository[RepoTenant](session)
    repo.add_all(
        [
            RepoTenant(name="mine"),
            RepoTenant(name="other", tenant=2),
            RepoTenant(name="gone", deleted_at=datetime.now(UTC)),
        ],
    )
    session.flush()

    assert sorted(row.name for row in repo.qs().with_deleted()) == ["gone", "mine"]
    assert [row.name for row in repo.qs()] == ["mine"]


def test_filter_by_order_by_limit_offset(session: Session) -> None:
    sales = _seed(session)
    qs = sales.qs().filter_by(percent=10).order_by(RepoSale.id)

    assert qs.first().id == 6
    assert qs.offset(2).first().id == 8
    assert [row.id for row in qs.limit(2)] == [6, 7]


def test_first_none_one_and_exists(session: Session) -> None:
    sales = _seed(session)

    assert sales.qs().where(RepoSale.id < 0).first() is None
    assert sales.qs().where(RepoSale.id == 7).one().id == 7
    assert sales.qs().where(RepoSale.id == 7).exists()
    assert not sales.qs().where(RepoSale.id == 3).exists()
    assert sales.qs().where(RepoSale.id > 40).count() == 10


def test_queryset_int_index_is_refused(session: Session) -> None:
    qs = _seed(session).qs()

    with pytest.raises(TypeError):
        qs[2]


def test_queryset_slices_are_forward_only(session: Session) -> None:
    qs = _seed(session).qs().order_by(RepoSale.id)

    assert [row.id for row in qs[0:3]] == [6, 7, 8]
    assert [row.id for row in qs[2:4]] == [8, 9]
    with pytest.raises(ValueError, match="forward"):
        qs[-1:]
    with pytest.raises(ValueError, match="forward"):
        qs[::2]


def test_select_escape_hatch_applies_criteria(session: Session) -> None:
    sales = _seed(session)

    rows = session.exec(sales.qs().where(RepoSale.id < 10).select).all()

    assert sorted(row.id for row in rows) == [6, 7, 8, 9]


def test_in_bulk_is_one_statement_and_keyed_by_id(session: Session) -> None:
    sales = _seed(session)
    engine = session.get_bind()

    with assert_statements(engine, 1):
        found = sales.qs().where(RepoSale.id.in_([6, 7, 3])).in_bulk()

    assert sorted(found) == [6, 7]
    assert found[6].id == 6


def test_in_bulk_by_columns(session: Session) -> None:
    sales = _seed(session)

    by_title = sales.qs().where(RepoSale.id.in_([6, 7])).in_bulk("title")
    by_pair = sales.qs().where(RepoSale.id.in_([6, 7])).in_bulk(("title", "percent"))

    assert sorted(by_title) == ["s6", "s7"]
    assert sorted(by_pair) == [("s6", 10), ("s7", 10)]


def test_bulk_soft_delete_is_one_update(session: Session) -> None:
    sales = _seed(session)
    engine = session.get_bind()

    with assert_statements(engine, 1):
        deleted = sales.qs().where(RepoSale.id.between(10, 19)).soft_delete()

    assert deleted == 10
    assert sales.qs().count() == 35


def test_bulk_update(session: Session) -> None:
    sales = _seed(session)

    changed = sales.qs().where(RepoSale.id > 45).update(percent=99)

    assert changed == 5
    assert sales[46].percent == 99
    assert sales[10].percent == 10


def test_bulk_purge(session: Session) -> None:
    sales = _seed(session)

    purged = sales.qs().only_deleted().purge()

    assert purged == 5
    assert sales.qs().with_deleted().count() == 45


def test_bulk_write_on_sliced_queryset_raises(session: Session) -> None:
    sales = _seed(session)

    with pytest.raises(TypeError, match="sliced"):
        sales.qs().limit(2).soft_delete()
    with pytest.raises(TypeError, match="sliced"):
        sales.qs().offset(2).update(percent=1)


def test_upsert_creates_restores_and_updates(session: Session) -> None:
    sales = _seed(session)

    result = sales.upsert(RepoSale(id=3 + i, title=f"new{i}", percent=99) for i in range(50))
    session.flush()

    assert all(isinstance(item, Upserted) for item in result)
    assert sum(item.created for item in result) == 2
    assert sum(item.restored for item in result) == 3
    assert sales[3].title == "new0"
    assert sales[3].deleted_at is None
    assert sales[52].title == "new49"
    assert result[0].restored
    assert not result[0].created


def test_upsert_statement_count_is_constant(session: Session) -> None:
    sales = _seed(session, total=200)
    engine = session.get_bind()
    counts = []
    for size in (5, 100):
        with count_statements(engine) as counter:
            sales.upsert(RepoSale(id=10 + i, title=f"x{size}", percent=size) for i in range(size))
            session.flush()
        counts.append((counter.selects, counter.count))

    assert counts[0][0] == counts[1][0] == 1
    assert counts[0][1] == counts[1][1]


def test_upsert_natural_key_matches_one_select(session: Session) -> None:
    tags = Repository[RepoTag](session)
    tags.add_all([RepoTag(owner="o", label="a", weight=1), RepoTag(owner="o", label="b", weight=1)])
    session.flush()
    engine = session.get_bind()

    with count_statements(engine) as counter:
        result = tags.upsert([RepoTag(owner="o", label="a", weight=5), RepoTag(owner="o", label="c", weight=5)])
        session.flush()

    assert counter.selects == 1
    assert [item.created for item in result] == [False, True]
    assert tags.qs().filter_by(owner="o", label="a").one().weight == 5


def test_upsert_custom_update_callback(session: Session) -> None:
    sales = _seed(session)

    def keep_percent(row: RepoSale, new: RepoSale) -> None:
        row.title = new.title

    sales.upsert([RepoSale(id=10, title="merged", percent=77)], update=keep_percent)
    session.flush()

    assert sales[10].title == "merged"
    assert sales[10].percent == 10


def test_upsert_empty_runs_nothing(session: Session) -> None:
    sales = Sales(session)

    with assert_statements(session.get_bind(), 0):
        assert sales.upsert([]) == []


class RepoBox(BaseModel, table=True):
    name: str = ""
    items = Relationship[list["RepoItem"]]()


class RepoItem(BaseModel, table=True):
    sku: str = ""
    price: int = 0
    note: str | None = None
    box = Relationship[Optional["RepoBox"]]()
    natural_key: ClassVar[tuple[str, ...]] = ("sku",)


configure([RepoBox, RepoItem])


class RepoGhost(BaseModel, table=True):
    name: str = ""
    natural_key: ClassVar[tuple[str, ...]] = ("name",)

    @classmethod
    def soft_delete_criteria(cls) -> ColumnElement[bool]:
        return cls.name != "ghost"


def test_upsert_without_update_keeps_fields_the_new_row_never_set(session: Session) -> None:
    items = Repository[RepoItem](session)
    items.add(RepoItem(sku="A", price=1, note="gift"))
    session.flush()

    items.upsert([RepoItem(sku="A", price=7)])

    stored = items.qs().where(RepoItem.sku == "A").one()
    assert (stored.price, stored.note) == (7, "gift")


def test_upsert_copies_a_field_explicitly_set_to_none(session: Session) -> None:
    items = Repository[RepoItem](session)
    items.add(RepoItem(sku="A", price=1, note="gift"))
    session.flush()

    items.upsert([RepoItem(sku="A", note=None)])

    stored = items.qs().where(RepoItem.sku == "A").one()
    assert (stored.price, stored.note) == (1, None)


def test_upsert_copies_a_generated_fk_column_only_when_set(session: Session) -> None:
    boxes = [RepoBox(name="one"), RepoBox(name="two")]
    session.add_all(boxes)
    session.flush()
    items = Repository[RepoItem](session)
    items.add(RepoItem(sku="A", box_id=boxes[0].id))
    session.flush()

    items.upsert([RepoItem(sku="A", price=2)])
    assert items.qs().one().box_id == boxes[0].id

    items.upsert([RepoItem(sku="A", box_id=boxes[1].id)])
    assert items.qs().one().box_id == boxes[1].id


def test_upsert_looks_keys_up_in_chunks(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loading, "CHUNK_SIZE", 3)
    items = Repository[RepoItem](session)
    items.add_all(RepoItem(sku=f"k{i}", price=1) for i in range(10))
    session.flush()

    with count_statements(session.get_bind()) as counter:
        result = items.upsert(RepoItem(sku=f"k{i}", price=2) for i in range(12))

    assert counter.count == 4
    assert sum(r.created for r in result) == 2
    assert sum(not r.created for r in result) == 10
    assert {row.price for row in items.qs().where(RepoItem.sku.in_([f"k{i}" for i in range(10)]))} == {2}


def test_slicing_composes_with_an_existing_offset_and_limit(session: Session) -> None:
    qs = _seed(session).qs().order_by(RepoSale.id)  # alive ids 6..50

    assert [r.id for r in qs.offset(10)[0:5]] == [16, 17, 18, 19, 20]
    assert [r.id for r in qs.offset(10)[2:4]] == [18, 19]
    assert [r.id for r in qs.offset(40)[2:]] == [48, 49, 50]
    assert [r.id for r in qs.limit(3)[0:10]] == [6, 7, 8]
    assert [r.id for r in qs.limit(10)[2:5]] == [8, 9, 10]
    assert qs.limit(3)[5:] == []
    assert [r.id for r in qs.offset(10).limit(4)[1:10]] == [17, 18, 19]


def test_where_after_limit_or_offset_raises(session: Session) -> None:
    qs = _seed(session).qs()

    with pytest.raises(TypeError, match="before"):
        qs.limit(3).where(RepoSale.id > 10)
    with pytest.raises(TypeError, match="before"):
        qs.offset(3).filter_by(percent=10)
    assert len(qs.where(RepoSale.id > 10).limit(3).all()) == 3


def test_overridden_soft_delete_criteria_is_read_by_with_deleted(session: Session) -> None:
    ghosts = Repository[RepoGhost](session)
    ghosts.add_all([RepoGhost(name="visible"), RepoGhost(name="ghost")])
    session.flush()

    assert [g.name for g in ghosts.qs()] == ["visible"]
    assert sorted(g.name for g in ghosts.qs().with_deleted()) == ["ghost", "visible"]
    assert [g.name for g in ghosts.qs().only_deleted()] == ["ghost"]


class RepoRedefined(BaseModel, table=True):
    name: str = ""

    @classmethod
    def default_criteria(cls) -> list[ColumnElement[bool]]:
        return [cls.name != "archived"]  # redefines what is hidden and drops soft_delete_criteria()


class RepoPlain(DataModel, table=True):
    name: str = ""


def test_with_and_only_deleted_refuse_a_model_that_redefines_default_criteria(session: Session) -> None:
    rows = Repository[RepoRedefined](session)

    with pytest.raises(TypeError, match=r"RepoRedefined.*override soft_delete_criteria\(\)"):
        rows.qs().with_deleted()
    with pytest.raises(TypeError, match=r"RepoRedefined.*override soft_delete_criteria\(\)"):
        rows.qs().only_deleted()


def test_with_deleted_is_a_no_op_and_only_deleted_refuses_a_model_without_soft_delete(session: Session) -> None:
    rows = Repository[RepoPlain](session)
    rows.add_all([RepoPlain(name="a", action=Actions.CREATE), RepoPlain(name="b", action=Actions.CREATE)])
    session.flush()

    assert sorted(row.name for row in rows.qs().with_deleted()) == ["a", "b"]
    with pytest.raises(TypeError, match="no deleted_at"):
        rows.qs().only_deleted()


def test_upsert_finds_a_row_hidden_by_an_overridden_soft_delete_criteria(session: Session) -> None:
    ghosts = Repository[RepoGhost](session)
    ghosts.add(RepoGhost(name="ghost"))
    session.flush()

    result = ghosts.upsert([RepoGhost(name="ghost")])

    assert result[0].created is False
    assert len(ghosts.qs().with_deleted().all()) == 1


def test_bulk_update_drops_cached_relationship_values(session: Session) -> None:
    boxes = [RepoBox(name="one"), RepoBox(name="two")]
    session.add_all(boxes)
    session.flush()
    session.add_all([RepoItem(sku="a", box_id=boxes[0].id), RepoItem(sku="b", box_id=boxes[0].id)])
    session.commit()
    items = Repository[RepoItem](session)
    item = items.qs().where(RepoItem.sku == "a").one()
    assert item.box is not None
    assert item.box.name == "one"
    assert len(boxes[0].items) == 2

    items.qs().where(RepoItem.sku == "a").update(box_id=boxes[1].id)

    assert item.box.name == "two"
    assert len(boxes[0].items) == 1


def test_bulk_soft_delete_and_purge_drop_cached_relationship_values(session: Session) -> None:
    box = RepoBox(name="one")
    session.add(box)
    session.flush()
    session.add_all([RepoItem(sku="a", box_id=box.id), RepoItem(sku="b", box_id=box.id), RepoItem(sku="c", box_id=box.id)])
    session.commit()
    items = Repository[RepoItem](session)
    assert len(box.items) == 3

    items.qs().where(RepoItem.sku == "a").soft_delete()
    assert len(box.items) == 2

    items.qs().where(RepoItem.sku == "b").purge()
    assert len(box.items) == 1


def test_list_of_a_queryset_or_repository_is_one_statement(session: Session) -> None:
    sales = _seed(session)
    engine = session.get_bind()

    with assert_statements(engine, 1):
        assert len(list(sales.qs())) == 45
    with assert_statements(engine, 1):
        assert len(list(sales)) == 45
    with assert_statements(engine, 1):
        assert len(sorted(sales.qs().with_deleted(), key=lambda row: row.id)) == 50
    with assert_statements(engine, 1):
        assert len(tuple(sales.qs())) == 45
    assert not hasattr(QuerySet, "__len__")
    assert not hasattr(Repository, "__len__")


def test_exists_on_an_empty_table_is_false_without_a_where_clause(session: Session) -> None:
    sales = Sales(session)
    plain = Repository[RepoPlain](session)

    assert sales.qs().exists() is False
    assert sales.qs().with_deleted().exists() is False  # only the soft-delete criterion was left, so no WHERE
    assert not sales.qs().with_deleted()
    assert plain.qs().exists() is False  # default_criteria() is empty
    assert not plain.qs()

    sales.add(RepoSale(id=1))
    plain.add(RepoPlain(name="a", action=Actions.CREATE))
    session.flush()

    assert sales.qs().with_deleted().exists() is True
    assert plain.qs().exists() is True


class TierBase[T: BaseModel](Repository[T]):
    pass


class TierMid[U: BaseModel](TierBase[U]):
    pass


class TierSales(TierBase[RepoSale]):
    pass


class TierDeepSales(TierMid[RepoSale]):
    pass


class TierPlainSales(TierSales):
    pass


def test_model_is_resolved_through_intermediate_generics(session: Session) -> None:
    assert TierSales(session).model is RepoSale
    assert TierDeepSales(session).model is RepoSale
    assert TierPlainSales(session).model is RepoSale
    assert TierBase[RepoTag](session).model is RepoTag


def test_unresolved_model_raises_at_class_creation() -> None:
    with pytest.raises(TypeError, match=r"Broken.*model"):

        class Broken(TierBase):  # type: ignore[type-arg]  # ty: ignore[invalid-argument-type]
            pass

    with pytest.raises(TypeError, match=r"Weird.*model"):

        class Weird(Repository[list[int]]):  # type: ignore[type-var]  # ty: ignore[invalid-type-arguments]
            pass


def test_delete_and_purge_drop_cached_relationship_values(session: Session) -> None:
    box = RepoBox(name="one")
    session.add(box)
    session.flush()
    session.add_all([RepoItem(sku=name, box_id=box.id) for name in "abc"])
    session.commit()
    items = Repository[RepoItem](session)
    a, b = (items.qs().where(RepoItem.sku == name).one() for name in "ab")
    assert sorted(item.sku for item in box.items) == ["a", "b", "c"]

    items.delete(a)
    assert sorted(item.sku for item in box.items) == ["b", "c"]

    items.purge(b)
    assert [item.sku for item in box.items] == ["c"]


def test_add_and_upsert_drop_cached_relationship_values(session: Session) -> None:
    box = RepoBox(name="one")
    session.add(box)
    session.flush()
    session.commit()
    items = Repository[RepoItem](session)
    assert list(box.items) == []

    items.add(RepoItem(sku="a", box_id=box.id))
    assert [item.sku for item in box.items] == ["a"]

    items.upsert([RepoItem(sku="b", box_id=box.id)])
    assert sorted(item.sku for item in box.items) == ["a", "b"]
