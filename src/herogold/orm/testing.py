"""Helpers for counting the SQL statements an engine runs, for query-count tests."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import event

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine

__all__ = ["StatementCounter", "assert_statements", "count_statements"]


class StatementCounter:
    """Record the SQL statements an engine executes while it is attached."""

    def __init__(self) -> None:
        """Start with no recorded statements."""
        self.statements: list[str] = []
        """SQL strings in execution order."""

    @property
    def count(self) -> int:
        """Return the number of recorded statements."""
        return len(self.statements)

    @property
    def selects(self) -> int:
        """Return the number of recorded statements that start with SELECT."""
        return sum(1 for statement in self.statements if statement.lstrip().upper().startswith("SELECT"))

    def _record(self, _conn: object, _cursor: object, statement: str, *_args: object) -> None:
        """Append one executed statement."""
        self.statements.append(statement)


@contextmanager
def count_statements(engine: Engine) -> Generator[StatementCounter]:
    """Count the statements `engine` executes inside the with block."""
    counter = StatementCounter()
    event.listen(engine, "before_cursor_execute", counter._record)  # noqa: SLF001
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", counter._record)  # noqa: SLF001


@contextmanager
def assert_statements(engine: Engine, expected: int) -> Generator[StatementCounter]:
    """Raise AssertionError, listing the statements, if the block does not run `expected` statements."""
    with count_statements(engine) as counter:
        yield counter
    if counter.count != expected:
        listing = "\n".join(f"  {i}. {statement}" for i, statement in enumerate(counter.statements, start=1))
        msg = f"expected {expected} statements, got {counter.count}:\n{listing}"
        raise AssertionError(msg)
