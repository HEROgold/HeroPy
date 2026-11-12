# Pinning `column=` on an existing plain column needs a migration note

A relationship that names an existing plain column, for example `guild = Relationship[Optional["Guild"]](column="guild_id")` where `guild_id` is an int holding a Discord ID, turns that column into a foreign key. We decided the ORM adds the foreign key to the table's metadata and does nothing else: no data check and no DDL. Alembic autogenerate then proposes an `add_fk` step, and the author of that revision writes a migration note saying that the existing rows were checked for values with no matching target. The foreign key cannot be applied while such rows exist.

An unpinned relationship never does this. If `<name>_id` exists as a plain column and `column=` is not given, the ORM raises and suggests either `column="<name>_id"` to make it a foreign key, or another name to get a separate column.

Enforcement is review only. In Winter Dragon the generated migration PR from the Auto-migrate workflow is where the note gets checked. We revisit this if notes get skipped.

## Considered options

- Attach the foreign key silently, with no note. Prototyped and rejected. A one-line pin would change a production schema, and adding a foreign key to a populated table fails or blocks writes if any row points at nothing. The declaration does not say any of that.
- Raise even when pinned, so the column must be declared as a foreign key by hand. Not chosen for now. It is the stricter fallback if migration notes are skipped.
