# A nested `begin()` joins the outer scope

`orm_session()` and `begin()` used to open a new session every time. A service that called another service therefore ran two transactions without anyone choosing that. In the prototype the inner block committed, the outer block then failed, and the inner rows stayed: a property with no sale.

We decided a `begin()` inside an open scope joins it when it runs on the same thread and task and uses the same engine (or none). The joined block runs in a SAVEPOINT, so an inner failure that the outer code catches undoes only the inner block. Only the outermost block commits.

- `begin(new=True)` opens an independent transaction on purpose, for example an audit row that must survive the outer rollback. It defaults to the outer scope's engine.
- `begin(savepoint=False)` skips the SAVEPOINT. If that block fails, the scope becomes rollback-only, and the outermost block rolls back and raises `ScopeRolledBack`, instead of committing half of the work.
- `begin(durable=True)` raises when a scope is already open, for code that must be the outermost transaction.
- A different engine, another thread or another asyncio task never joins. A task created inside a scope copies the context and so would otherwise inherit a session that is not safe to share.
- `on_commit(fn)` runs `fn` after the outermost commit. A rollback discards it, and so does a rolled-back SAVEPOINT block. Outside any scope it runs at once.

Django's `transaction.atomic()` has the same shape: nested blocks use savepoints, `savepoint=False` and `durable=True` exist, and `on_commit` runs after the outermost commit. We follow it on purpose, so people who know Django find no surprises.

## Considered options

- Keep opening a new session on every call. Rejected: it caused the orphan row above.
- Join without a SAVEPOINT. Rejected as the default: a swallowed inner failure would leave its half-written changes in the outer transaction. It stays available as `savepoint=False`, with the rollback-only guard.
- Forbid nesting. Rejected as the default, since services that call each other are normal. It stays available as `durable=True`.
