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


class DescriptorMeta(type(Protocol)):
    """Metaclass validating Python's core descriptor definition."""

    def __instancecheck__(cls, instance: object) -> bool:
        """Check if instance is a descriptor by verifying the presence of __get__, __set__, or __delete__."""
        return isinstance(instance, (SupportsGet, SupportsSet, SupportsDelete))


class DataDescriptorMeta(type(Protocol)):
    """Metaclass validating Python's data descriptor definition.

    A data descriptor overrides __dict__ if it has __set__ OR __delete__.
    """

    def __instancecheck__(cls, instance: object) -> bool:
        """Check if data descriptor overrides __dict__ if it has __set__ OR __delete__."""
        return isinstance(instance, (SupportsSet, SupportsDelete))


class NonDataDescriptorMeta(type(Protocol)):
    """Metaclass validating Python's non-data descriptor definition."""

    def __instancecheck__(cls, instance: object) -> bool:
        """Check if non-data descriptor has __get__ without __set__ or __delete__."""
        return isinstance(instance, SupportsGet) and not isinstance(instance, (SupportsSet, SupportsDelete))


class Descriptor[Value, Owner](
    SupportsGet[Value, Owner],
    SupportsSet[Value, Owner],
    SupportsDelete[Value, Owner],
    Protocol,
    metaclass=DescriptorMeta,
):
    """General Descriptor: Resolves if __get__, __set__, OR __delete__ are present."""


class DataDescriptor[Value, Owner](
    SupportsSet[Value, Owner],
    SupportsDelete[Value, Owner],
    Protocol,
    metaclass=DataDescriptorMeta,
):
    """Data Descriptor: Resolves if __set__ OR __delete__ are present."""


class NonDataDescriptor[Value, Owner](
    SupportsGet[Value, Owner],
    Protocol,
    metaclass=NonDataDescriptorMeta,
):
    """Non-Data Descriptor: Resolves if __get__ is present WITHOUT __set__ or __delete__."""

type DescriptorType[Value, Owner] = SupportsGet[Value, Owner] | SupportsSet[Value, Owner] | SupportsDelete[Value, Owner]
type DataDescriptorType[Value, Owner] = SupportsSet[Value, Owner] | SupportsDelete[Value, Owner]
type NonDataDescriptorType[Value, Owner] = SupportsGet[Value, Owner] # & ~SupportsSet[Value, Owner] & ~SupportsDelete[Value, Owner]
