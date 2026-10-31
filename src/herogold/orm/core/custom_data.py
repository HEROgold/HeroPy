"""The CustomData table, which stores extra JSONB data for any model."""

from __future__ import annotations

from typing import Any, Self, override

from sqlalchemy import JSON, Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session

from herogold.orm.core.base_model import _BaseModel


class CustomData(_BaseModel, table=True):
    """Persisted extra-data table: a single JSONB blob per row.

    Every model links to (at most) one ``CustomData`` row through the inherited
    ``custom_data`` relationship. It is defined right after ``_BaseModel`` so it
    exists as a link target before any concrete model, and it is built *before*
    the ``custom_data`` relationship is attached to ``_BaseModel`` below, so it
    stays a leaf (no recursive self-link).
    """

    # JSONB on PostgreSQL, plain JSON elsewhere (e.g. the sqlite test engine).
    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON().with_variant(JSONB(), "postgresql")),
    )

    @override
    def _create_record(self, session: Session) -> None:
        self.logger.debug("Creating record: %s", self, extra={"record": self})
        session.add(self)
        session.commit()

    @override
    def _update_record(self, session: Session, entry: Self) -> None:
        entry.data = self.data
        session.add(entry)
        session.commit()

    @override
    def _delete_record(self, session: Session) -> None:
        session.delete(self)
        session.commit()
