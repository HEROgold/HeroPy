"""Types for compound objects from the supports module.

These usually represent more complex protocols that combine multiple supports protocols into a single type.
"""
from __future__ import annotations

from herogold.supports import SupportsDelete, SupportsGet, SupportsSet

type DescriptorType[Value, Owner] = SupportsGet[Value, Owner] | SupportsSet[Value, Owner] | SupportsDelete
type DataDescriptorType[Value, Owner] = SupportsSet[Value, Owner] | SupportsDelete
type NonDataDescriptorType[Value, Owner] = (
    SupportsGet[Value, Owner]
    & ~SupportsSet[Value, Owner]  # ty:ignore[experimental-syntax, unsupported-operator]
    & ~SupportsDelete  # ty:ignore[experimental-syntax]
)
