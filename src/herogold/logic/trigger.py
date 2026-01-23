"""Module defining the Trigger class for conditional action execution."""
from typing import Generic, TypeVar

from herogold.logic.action import Action
from herogold.logic.predicate import Predicate
from herogold.sentinel import create_sentinel

T = TypeVar("T")
DidNotRun = create_sentinel() # Sentinel value indicating the action did not run

class Trigger(Generic[T]):
    """A trigger that activates an action based on a condition."""

    __slots__ = ("action", "condition")

    def __init__(self, condition: Predicate, action: Action[T]) -> None:
        """Initialize the trigger with a name, condition, and action."""
        self.condition = condition
        self.action = action

    def __call__(self) -> T | DidNotRun:
        """Check the condition and execute the action if the condition is met."""
        if self.condition():
            return self.action()
        return DidNotRun
