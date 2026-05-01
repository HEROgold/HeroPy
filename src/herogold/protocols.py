"""Protocols for compound objects from the supports module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from herogold.supports import (
    SupportsDelete,
    SupportsGet,
    SupportsSet,
)


@runtime_checkable
class Container[Owner, Value](SupportsGet[Value, Owner], SupportsSet[Value, Owner], Protocol):
    """A protocol for container types that support getting and setting items."""


@runtime_checkable
class Descriptor[Value, Owner](SupportsGet[Value, Owner], Protocol):
    """A protocol for descriptor objects that support getting a value.

    Owner type should be `object`, as it's common for descriptors to not care about the owner type.
    but it may be specified for more precise typing.
    """


@runtime_checkable
class DataDescriptor[Value, Owner](Descriptor[Value, Owner], SupportsSet[Value, Owner], SupportsDelete[Value, Owner], Protocol):
    """A protocol for data descriptors that support getting, setting, deleting, and naming.

    Data descriptors are descriptors that define __set__() or __delete__(). They take precedence over instance attributes.
    """
