"""Protocols for compound objects from the supports module."""

from __future__ import annotations

from ._protocols import (
    Container,
    DataDescriptor,
    DataDescriptorMeta,
    Descriptor,
    DescriptorMeta,
    NonDataDescriptor,
    NonDataDescriptorMeta,
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
    "NonDataDescriptor",
    "NonDataDescriptorMeta",
    "NonDataDescriptorType",
    "URLSpec",
]
