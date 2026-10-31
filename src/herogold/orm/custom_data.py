"""Size limit and caller-session writes for the ``CustomData`` extra-data table.

The persisted ``CustomData`` table lives in :mod:`herogold.orm.core.custom_data`.
:func:`set_custom_data` writes it in the caller's session (or an owned one) and
links it to an owner, without importing FastAPI.
"""

from __future__ import annotations

import json
from typing import Any

from herogold.errors import HerogoldError
from herogold.orm.core.base_model import _BaseModel  # noqa: TC001  # inject resolves annotations at runtime
from herogold.orm.core.binding import OwnedSession  # noqa: TC001  # inject resolves annotations at runtime
from herogold.orm.core.custom_data import CustomData
from herogold.typing.inject import inject

DEFAULT_SIZE_LIMIT = 1024 * 10
"""Default byte budget for a model's custom data (the old descriptor default)."""


class OutOfSpaceError(HerogoldError, ValueError):
    """Raised when the custom data exceeds the size limit."""

    def __init__(self, size: int, limit: int) -> None:
        """Initialize the OutOfSpaceError with the size and limit."""
        super().__init__(f"Custom data of size {size} exceeds limit of {limit} bytes.")


def validate_size(data: Any, size_limit: int = DEFAULT_SIZE_LIMIT) -> None:  # noqa: ANN401
    """Raise :class:`OutOfSpaceError` when the serialised ``data`` is over ``size_limit`` bytes.

    The size is the UTF-8 byte length of the compact ``json.dumps`` output, so
    nested values count in full.

    Raises:
        OutOfSpaceError: If the serialised size is greater than ``size_limit``.

    """
    size = len(json.dumps(data, separators=(",", ":")).encode("utf-8"))
    if size > size_limit:
        raise OutOfSpaceError(size, size_limit)


@inject
def set_custom_data(item: _BaseModel, data: dict[str, Any], session: OwnedSession = None) -> CustomData:
    """Store ``data`` as ``item``'s custom data, linked in the caller's session.

    Validates the size against the model's ``custom_data_size_limit`` (default
    :data:`DEFAULT_SIZE_LIMIT`), creates a :class:`CustomData` row, and replaces
    the owner's link. A second call replaces the link rather than merging.

    The function flushes but never commits. With no ``session``, an owned session
    is opened and committed by :func:`herogold.orm.core.binding.orm_session`.

    Args:
        item: A persisted owner model instance.
        data: JSON-serialisable mapping to store.
        session: Caller's session. ``@inject`` opens an owned one when omitted.

    Returns:
        The new ``CustomData`` row.

    Raises:
        OutOfSpaceError: If ``data`` is over the model's size limit. Nothing is written.

    """
    limit = getattr(type(item), "custom_data_size_limit", DEFAULT_SIZE_LIMIT)
    validate_size(data, limit)
    row = CustomData(data=data)
    session.add(row)
    session.flush()
    type(item).custom_data.link(item, row, session=session)
    return row
