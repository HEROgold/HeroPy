"""Types for compound objects from the supports module.

These usually represent more complex protocols that combine multiple supports protocols into a single type.
"""

from __future__ import annotations

from herogold.supports import SupportsDelete, SupportsGet, SupportsSet

type DataDescriptorType[Value, Owner] = SupportsSet[Value, Owner] | SupportsDelete
type NonDataDescriptorType[Value, Owner] = SupportsGet[Value, Owner]
type DescriptorType[Value, Owner] = DataDescriptorType[Value, Owner] | NonDataDescriptorType[Value, Owner]
