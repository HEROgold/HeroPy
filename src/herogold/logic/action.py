"""Defines an Action class and a decorator to create actions from functions."""
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

class Action[T]:
    """An action to be executed."""

    __slots__ = ("func",)

    def __init__(self, func: Callable[P, T]) -> None:
        """Initialize the action with a callable function."""
        self.func = func

    def __call__(self) -> T:
        """Execute the action and return its result."""
        return self.func()


def action[**P, T](func: Callable[P, T]) -> Action[T]:
    """Decorate a method to create an Action instance from it."""
    return Action(func)
