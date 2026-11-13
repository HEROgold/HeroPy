# Relationships

A typed relationship is a class attribute whose type argument says what it points at. Run `configure()` once, and the ORM pairs the two sides, adds the foreign-key columns or link tables, and loads related rows in batches.

## Declaring

```python
from __future__ import annotations

from typing import Optional

from herogold.orm import BaseModel, Relationship, configure


class Team(BaseModel, table=True):
    name: str
    players = Relationship[list["Player"]]()


class Player(BaseModel, table=True):
    name: str
    team = Relationship[Optional["Team"]]()


configure()
```

`Relationship[Optional["Team"]]()` holds one row or `None`. `Relationship[list["Player"]]()` holds many rows. Quote a name that is defined later in the module, because the class body evaluates the subscript.

Do not annotate the attribute. SQLModel turns an annotated class attribute into a column.

Call `configure()` after the last model is imported and before anything reads the metadata. Nothing calls it for you. It needs no database, so it is safe to call again after more models load. It only adds what is missing.

`configure(models=[...])` limits the run to the relationships declared on those classes, plus the relationships that point back at them. A pair is always judged with both sides, so configuring one model of a pair never gives it a link table of its own.

Both the owner and the target of a relationship need a single-column primary key. `configure()` raises `RelationshipConfigurationError` for a composite one.

In this example `Player` gets a `team_id` column with a foreign key to `team.id`. `Team.players` reads that column, so it needs no storage of its own.

## Pairing

Two relationships are a pair when each is the only automatic one from its model to the other. `Team.players` and `Player.team` above are a pair, so one `team_id` column serves both. A write through one side shows up on the other side if that row is in memory.

Pairing looks at types only. Two unrelated relationships between the same models pair when each is the only one.

`inverse=` overrides this.

```python
class Channel(BaseModel, table=True):
    guild = Relationship[Optional["Guild"]](inverse=lambda: Guild.channels)


class Guild(BaseModel, table=True):
    channels = Relationship[list["Channel"]]()
    main = Relationship[Optional["Channel"]](inverse=None)
```

- `inverse=Guild.channels` pins the pair. Pass a lambda when the other class is defined later.
- `inverse=None` keeps the relationship out of every pair.

If the automatic relationships between two models are not exactly one each way, every one of them fails, and `configure()` raises `RelationshipConfigurationError`:

```python
class Match(BaseModel, table=True):
    home = Relationship[Optional["Team"]]()
    away = Relationship[Optional["Team"]]()


class Team(BaseModel, table=True):
    last_match = Relationship[Optional["Match"]]()
```

```
Match.home: Match.home, Match.away, Team.last_match could pair in several ways; pin one with inverse=<relationship>, or opt out with inverse=None
```

The same message is raised for `Match.away` and `Team.last_match`.

The exception's `errors` attribute maps `Owner.attribute` to each message. Relationships that did not fail are configured before the exception is raised. Reading a relationship that failed raises its message as a `LookupError`.

## Choosing the column

A single-valued relationship stores a foreign-key column on its owner. `configure()` picks the column in this order.

1. The name given in `column=`. It is a string, or a lambda returning the mapped column.
2. The only foreign key to the target that you declared yourself.
3. A generated column named `<name>_id`, nullable for `Optional`.

It raises instead of guessing when you declared several foreign keys to the target and none is named `<name>_id`. It also raises when a plain column named `<name>_id` exists and `column=` is not given, because a plain `guild_id` integer that holds a Discord ID must not become a foreign key by accident.

```python
class Guild(BaseModel, table=True):
    main = Relationship[Optional["Channel"]](inverse=None, column="main_channel_id")
```

In a one-to-one pair, exactly one side pins `column=` or declares a foreign key. Both or neither raises.

A many-valued relationship follows the column of its paired single-valued side. A list that nothing points back to uses the only unclaimed foreign key from the target, or else a link table. Two paired lists use a link table named `<owner table>_<name>`, with composite primary key `owner_id`, `target_id`.

`Relationship.placement` on the class tells you what `configure()` chose.

### Pinning a column that already exists

`column="guild_id"` on an existing plain column attaches a foreign key to it. The ORM changes the table metadata only. It checks no data and runs no DDL. Alembic autogenerate then proposes a new constraint, and the existing rows must have no value without a matching target. See [ADR 0002](../adr/0002-pinning-a-column-on-a-plain-column-needs-a-migration-note.md) and the migration note in the [release notes](release-notes.md).

## Loading

Rows that one `SELECT` returns form a cohort. The first read of a relationship on any member loads it for every member of the cohort that is still in memory, with one `IN` query per 500 rows.

```python
teams = session.exec(select(Team)).all()
names = {team.name: [p.name for p in team.players] for team in teams}  # 1 statement for all teams
```

Reading `team.players` for 3 teams and for 300 teams runs the same number of statements, up to 500 teams per chunk. Loaded values are cached on the instances and dropped on commit and rollback.

### Counting statements in tests

`herogold.orm` has three helpers for query-count tests.

```python
from herogold.orm import assert_statements, count_statements, forbid_unbatched_loads

with count_statements(engine) as counter:
    ...
counter.count    # all statements
counter.selects  # statements that start with SELECT
counter.statements  # the SQL strings

with assert_statements(engine, 1):  # raises AssertionError and lists the statements if the count differs
    ...

with forbid_unbatched_loads():  # a load no other row shares raises UnbatchedLoadError
    ...
```

`forbid_unbatched_loads()` is the test-mode counterpart of SQLAlchemy's `lazy="raise"`. A load is unbatched when its row came from a query that returned no other row still in memory.

### Soft-deleted targets

A load applies the target's `default_criteria()`. For `BaseModel` that includes `deleted_at IS NULL`, so a soft-deleted team reads as `None` from `player.team`, and a soft-deleted player is missing from `team.players`. The foreign-key column keeps its value. Use a `Repository` query with `with_deleted()` to reach deleted rows.

### Required relationships read as None

A single-valued relationship without `Optional` is required. A required relationship with no linked row still reads as `None`, and the read does not raise. "Required" applies when a row is written. `configure()` makes the generated `<name>_id` column `NOT NULL`, so inserting an owner without a target fails with the database's `IntegrityError`. Reading has to stay lenient, because rows are legitimately half built: a new owner has no target before it is flushed, and a stored foreign key can point at a row the session cannot see. SQLAlchemy behaves the same way for a many-to-one with a null foreign key.

## Writing
A many-valued relationship reads as a `RelatedList`. It behaves as a list with these differences.

- `append`, `extend`, `remove`, `clear`, `pop`, `del` and `+=` write to the database. Appending a row that is already in the list does nothing.
- `insert` and item assignment raise `TypeError`, because the database stores no order. Assigning a whole list (`team.players = [...]`) raises too. Use `clear()` and `extend()`.
- The owner must be in a session, or the call raises `RuntimeError`.
- `copy.copy()` and `copy.deepcopy()` return a plain `list`. The copy writes nothing.

Assigning a single-valued relationship (`player.team = team`, or `None`) writes the same way and keeps the paired side in step.

Nothing here commits. A write is queued on the owner's session and applied at these points.

1. `before_flush`, for writes whose rows already have ids.
2. `after_flush_postexec`, for writes that waited for ids a flush assigned.
3. `before_commit`.
4. Before a read of any typed relationship on the same session.

So `team.players.append(player)` with two new rows needs no manual flush. A column write whose id is known is a plain attribute set. When the id only exists after a flush, the write waits and then runs as one `UPDATE` per column and chunk of rows. Link-table writes run on `session.connection()` inside the caller's transaction, one statement per consecutive run of the same kind.

Reading the relationship first applies the queued writes, so the list you read matches what you wrote.

`pop`, `del x[i]`, `del x[a:b]` and `x += items` write through like `remove` and `extend`. `+=` keeps the same list object, and a rollback undoes it.

### Link-only changes and flush

A change that only touches a link table, such as `post.tags.append(tag)` on a session with no other dirty row, has nothing for `session.flush()` to write, so `flush()` alone does not apply it. A read of any typed relationship on the same session applies it, and so does `commit()`. A raw SQL read through `session.execute()` does not apply it. Read a typed relationship first, or commit, before you count link rows.
