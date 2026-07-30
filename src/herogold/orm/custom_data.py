"""Helpers for the ``CustomData`` extra-data table.

The persisted ``CustomData`` table itself lives in :mod:`herogold.orm.model`;
this module only holds the size-limit helpers so they can be imported without a
circular dependency.
"""
from __future__ import annotations

from sys import getsizeof
from typing import TYPE_CHECKING

from herogold.errors import with_known_exception

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_SIZE_LIMIT = 1024 * 10
"""Default byte budget for a model's custom data (the old descriptor default)."""


class OutOfSpaceError(ValueError):
    """Raised when the custom data exceeds the size limit."""

    def __init__(self, size: int, limit: int) -> None:
        """Initialize the OutOfSpaceError with the size and limit."""
        super().__init__(f"Custom data of size {size} exceeds limit of {limit} bytes.")


@with_known_exception(OutOfSpaceError)
def validate_size(item: Mapping[object, object], size_limit: int = DEFAULT_SIZE_LIMIT) -> None:
    """Validate that the size of the custom data does not exceed the limit.

    Returns an :class:`OutOfSpaceError` instead of raising it (see
    :func:`herogold.errors.with_known_exception`); callers must inspect the
    return value and decide how to react to an overflow.
    """
    if getsizeof(item) > size_limit:
        raise OutOfSpaceError(getsizeof(item), size_limit)
