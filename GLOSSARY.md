# herogold.orm

The ORM layer of herogold: models that act as repositories over a database the app chooses.

## Language

### Database access

**Binding**:
The engine the app has attached to the ORM. Every model reads and writes through it.
_Avoid_: global engine, default engine, connection

**Caller session**:
A session the app passes into an ORM call. The app owns its transaction, so the ORM never commits it.
_Avoid_: external session, user session

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
