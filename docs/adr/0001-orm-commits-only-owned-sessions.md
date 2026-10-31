# The ORM commits only sessions it opened itself

Every ORM write (`add`, `update`, `delete`, relationship links, custom data) used to commit whatever session it was given, so an app could not group a signup, its links and its custom data into one transaction. We decided the ORM commits only an owned session, one it opened for a single call because the caller passed none. A caller session gets `flush()` so ids are assigned, and the caller decides when to commit. Callers that passed `session=` and relied on the implicit commit must now commit themselves (breaking, 7.0.0).

## Considered options

- Stop committing only inside `Relationship`. Rejected because `add` would still commit mid-transaction, which brings back the non-atomic signup.
- A `commit=False` opt-out. Rejected because the safe behaviour should be the default, not a flag every caller has to remember.
