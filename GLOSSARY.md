# herogold.orm

The ORM layer of herogold: models that act as repositories over a database the app chooses.

## Language

### Database access

**Binding**:
The engine the app has attached to the ORM. Every model reads and writes through it.
_Avoid_: global engine, default engine, connection

**Caller session**:
A session the app controls: one passed into an ORM call, or the one an owner was loaded in. The ORM never commits it.
_Avoid_: external session, user session

**Request session**:
The session the API layer opens for one HTTP request. It commits when the handler succeeds and rolls back when it fails.

**Owned session**:
A short-lived session the ORM opens for a single call when no caller session is given. It is committed and closed before the call returns.
_Avoid_: default session, class session, shared session

### Relationships

**Owner**:
The model instance that holds a relationship attribute, such as the Invite in `invite.account`.
_Avoid_: source, parent (except for self-relationships)

**Target**:
The model instance an owner points at through a relationship, such as the Account in `invite.account`.
_Avoid_: related model, value, destination

**Link**:
The single stored association between one owner and one target for one relationship attribute.
_Avoid_: relation, association, join

**Custom data**:
A free-form JSON payload attached to any model instance through a link, limited to a byte budget per model.
_Avoid_: extra data, metadata, blob

**Cohort**:
The rows one query returned that are still in memory in one session. The first read of a relationship on any member loads it for all of them with one query.
_Avoid_: batch, result set

**Related list**:
The list a many-valued relationship returns. Appending to it or removing from it writes through the owner's session and never commits.
_Avoid_: collection, backref

### Transactions

**Scope**:
One transaction around a block of code, opened with `orm_session()` or `Scoped.begin()`. The outermost scope commits or rolls back, and a scope opened inside it joins it in a SAVEPOINT.
_Avoid_: unit of work, atomic block

**Configure**:
The one call, `configure()`, that pairs typed relationships and generates their columns and link tables. It runs after the last model is imported and before `create_all` or Alembic.
_Avoid_: init, setup, register
