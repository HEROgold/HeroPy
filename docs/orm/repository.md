# Repository and QuerySet

A `Repository` reads and writes the rows of one model through a session you give it. It never commits. A `QuerySet` is an immutable, chainable query that hides rows excluded by the model's `default_criteria()`, which means soft-deleted rows for `BaseModel`.

## Repository

Subclass it with the model as the type argument, or build one directly.

```python
from herogold.orm import Repository


class Sales(Repository[Sale]):
    pass


sales = Sales(session)
sales = Repository[Sale](session)
```

The model can come through generic intermediate classes: with `class Base[T: BaseModel](Repository[T])`, `class Sales(Base[Sale])` serves `Sale`. A subclass whose model is not a class and that is not generic itself raises `TypeError` when the class is created. A `Repository` without a model raises `TypeError` when it first needs one. To open a session and a repository in one step, add the `Scoped` mixin (see [Scopes](scopes.md)).

```python
sale = sales.add(Sale(title="spring"))  # session.add, returns the row
sales.add_all([Sale(title="a"), Sale(title="b")])
sales.delete(sale)  # soft delete when the model has deleted_at, else a real delete
sales.purge(sale)   # always a real DELETE
```

`add`, `add_all`, `delete`, `purge` and `upsert` drop the cached relationship values of the session, as the bulk writes do, so `team.players` reads the change on its next access.

A repository is a collection of the alive rows, looked up by id.

| Expression | Result |
|---|---|
| `bool(sales)` | One `EXISTS` statement |
| `5 in sales`, `sale in sales` | Whether that id or row is alive |
| `sales[5]` | The alive row with id 5. `KeyError` if absent or deleted |
| `del sales[5]` | Soft-deletes that row, or deletes it without `deleted_at`. `KeyError` if no alive row has the id |
| `for sale in sales` | Loads and yields every alive row |

`sales[2:5]` raises `TypeError`, because a slice of a repository would read as ids. Slice a queryset instead: `sales.qs()[2:5]`.

Neither a repository nor a queryset has `len()`. Python calls `len()` on the argument of `list()`, `tuple()` and `sorted()` as a size hint, so `list(sales)` would run a `COUNT` before the `SELECT`. Count with `sales.qs().count()`.

## QuerySet

`sales.qs()` returns a queryset of alive rows. Every builder returns a new queryset.

```python
cheap = sales.qs().where(Sale.price < 10).order_by(Sale.title).limit(20)
```

| Builder | Effect |
|---|---|
| `where(*criteria)` | Narrow by SQL expressions |
| `filter_by(**kwargs)` | Narrow by column equality |
| `order_by(*columns)` | Order |
| `limit(n)`, `offset(n)` | Page. Marks the queryset as sliced |
| `with_deleted()` | Include soft-deleted rows |
| `only_deleted()` | Only soft-deleted rows. `TypeError` without `deleted_at` |

| Terminal | Result |
|---|---|
| `all()`, `list(qs)`, `for row in qs` | A list of rows, one `SELECT` |
| `first()` | The first row or `None` |
| `one()` | The only row. Raises when there are none or several |
| `exists()`, `bool(qs)` | One `EXISTS` statement |
| `count()` | One `COUNT` statement |
| `in_bulk(by="id")` | `dict` keyed by one column, or by a tuple when `by` is a tuple of names. One statement |
| `qs[a:b]` | A list. Forward slices only. `qs[7]` raises `TypeError` |
| `item in qs` | Whether a row or an id matches, with `EXISTS` |
| `qs.select` | The raw `Select` with the model criteria applied |

Bulk writes run one statement and return the row count.

```python
sales.qs().where(Sale.price == 0).update(price=1)
sales.qs().filter_by(title="old").soft_delete()  # sets deleted_at; TypeError without that column
sales.qs().filter_by(title="old").purge()        # DELETE
```

They raise `TypeError` on a sliced queryset. Rows already in the session are refreshed to match.

`with_deleted()` and `only_deleted()` remove only the entry of `default_criteria()` that equals `soft_delete_criteria()`. Other entries, such as a tenant filter, still apply. A model that redefines "deleted" in `default_criteria()` without an entry equal to `soft_delete_criteria()` gets a `TypeError` from both calls, because the library cannot tell which entry hides deleted rows. Override `soft_delete_criteria()` to return that criterion, or include `soft_delete_criteria()` in `default_criteria()`. A model with no soft delete at all keeps `with_deleted()` as a no-op, and `only_deleted()` raises `TypeError`.

## Upsert

`upsert` adds new rows and updates stored ones in a single pass.

```python
class Sale(BaseModel, table=True):
    natural_key = ("title",)
    title: str
    price: int = 0


results = sales.upsert([Sale(title="spring", price=5), Sale(title="summer", price=7)])
for result in results:
    print(result.row.title, result.created, result.restored)
```

- It matches rows on the model's `natural_key` (a tuple of field names), or on `id` when the tuple is empty. A row with an unset key field never matches and is added.
- One `SELECT` finds the stored rows, soft-deleted ones included.
- A match is un-deleted (`restored=True`) and gets the new row's field values. `id`, `created_at`, `updated_at` and `deleted_at` are not copied.
- Pass `update=fn` to replace the copy: `fn(stored, new)` runs for each match.
- A row without a match is added (`created=True`).
- Nothing is committed. The caller commits, or the enclosing scope does.

`upsert` returns a list of `Upserted(row, created, restored)` in input order.
