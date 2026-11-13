# ORM release notes

This release adds typed relationships, batched loading, repositories and transaction scopes to `herogold.orm`. The version number is set when the release PR merges.

## New

- Typed relationships: `Relationship[Optional["Team"]]()` and `Relationship[list["Player"]]()`. `configure()` pairs them and generates the foreign-key columns and link tables. See [Relationships](relationships.md).
- Batched loading. The first read of a relationship loads it for every row the same query returned, with one `IN` query per 500 rows. `count_statements`, `assert_statements` and `forbid_unbatched_loads` in `herogold.orm` test this.
- Related lists. `team.players.append(player)` writes through the owner's session and never commits.
- `Repository` and `QuerySet`, with soft-delete aware queries, bulk `update`, `soft_delete` and `purge`, and `upsert`. See [Repository and QuerySet](repository.md).
- Scopes: `orm_session()`, `Scoped.begin()`, `bind()`, `on_commit()` and the `@transactional` decorator. Nested scopes join the outer transaction in a SAVEPOINT. See [Scopes](scopes.md).
- ADRs [0002](../adr/0002-pinning-a-column-on-a-plain-column-needs-a-migration-note.md) and [0003](../adr/0003-a-nested-begin-joins-the-outer-scope.md).

## Migration note

Pinning `column=` on a column that already exists as a plain column attaches a foreign key to it. Alembic autogenerate proposes a new constraint for it. Before you apply that revision, check that no existing row holds a value with no matching row in the target table, because the constraint cannot be created while such rows exist. State in the revision that you checked. A relationship without `column=` never does this: it raises and asks you to choose.

Run `configure()` before `create_all` and before Alembic reads the metadata. Add it to `env.py`.

## Unchanged

The old form, `Relationship(Target)`, works as before and keeps its association table. Existing models need no change. Type checkers type it as `Target | None`, while the new form types instances as the declared type.
