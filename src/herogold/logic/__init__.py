"""Logic module helping with logical operations."""

from __future__ import annotations

from .action import Action, action
from .predicate import Predicate, predicate
from .trigger import DidNotRun, Trigger

__all__ = [
    "Action",
    "DidNotRun",
    "Predicate",
    "Trigger",
    "action",
    "predicate",
]
