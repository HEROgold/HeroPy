"""Engine binding for the ORM.

The application supplies an engine with :func:`bind`. Model methods that are not
given a session open an owned one through :func:`orm_session`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Annotated

import sqlmodel
from sqlalchemy.orm import sessionmaker

from herogold.typing.inject import Depends

from .errors import NoEngineBoundError

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

__all__ = ["OwnedSession", "bind", "bound", "orm_session"]

_factory: sessionmaker[sqlmodel.Session] | None = None


def bind(engine: Engine) -> None:
    """Bind the ORM to ``engine``. The ORM never disposes the engine."""
    global _factory  # noqa: PLW0603
    _factory = sessionmaker(engine, class_=sqlmodel.Session, expire_on_commit=False)


@contextmanager
def bound(engine: Engine) -> Iterator[None]:
    """Bind ``engine`` inside the block, then restore the previous binding."""
    previous = _factory
    bind(engine)
    try:
        yield
    finally:
        _restore(previous)


def _restore(previous: sessionmaker[sqlmodel.Session] | None) -> None:
    global _factory  # noqa: PLW0603
    _factory = previous


@contextmanager
def orm_session() -> Iterator[sqlmodel.Session]:
    """Open a session on the bound engine.

    Commits when the block succeeds, rolls back when it raises, and always closes.

    Raises:
        NoEngineBoundError: If no engine is bound.

    """
    factory = _factory
    if factory is None:
        msg = "No engine is bound. Call herogold.orm.bind(engine) first."
        raise NoEngineBoundError(msg)
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


OwnedSession = Annotated[sqlmodel.Session | None, Depends(orm_session)]
"""Session parameter type. ``@inject`` fills it with an owned session when the caller passes none."""
