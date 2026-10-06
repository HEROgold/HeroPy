"""Protocols for compound objects from the supports module."""

from __future__ import annotations

from ._protocols import (
    Container,
    DataDescriptor,
    DataDescriptorMeta,
    Descriptor,
    DescriptorMeta,
    Filterable,
    NonDataDescriptor,
    NonDataDescriptorMeta,
    Sortable,
)
from .types import DataDescriptorType, DescriptorType, NonDataDescriptorType
from .url_specification import URLSpec

__all__ = [
    "Container",
    "DataDescriptor",
    "DataDescriptorMeta",
    "DataDescriptorType",
    "Descriptor",
    "DescriptorMeta",
    "DescriptorType",
    "Filterable",
    "NonDataDescriptor",
    "NonDataDescriptorMeta",
    "NonDataDescriptorType",
    "Sortable",
    "URLSpec",
]
