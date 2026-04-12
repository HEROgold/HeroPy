"""State machine implementation for handling state transitions.

Copied and modified from: https://github.com/ArjanCodes/examples/blob/main/2026/state/final.py
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum

from herogold.log.logger_mixin import LoggerMixin

type Action[Context] = Callable[[Context], None]
type CurrentState[State, Event] = tuple[State, Event]
type NextState[State, Action] = tuple[State, Action]
type Transition[State, Event, Context] = dict[CurrentState[State, Event], NextState[State, Action[Context]]]
type TransitionDecorator[Context] = Callable[[Action[Context]], Action[Context]]


class InvalidTransitionError(Exception):
    """Raised when an invalid transition is attempted."""


@dataclass
class StateMachine[State: Enum, Event: Enum, Context](LoggerMixin):
    """State machine for handling state transitions."""

    transitions: Transition[State, Event, Context] = field(default_factory=dict)

    def _add(
        self,
        from_: State,
        event: Event,
        to: State,
        func: Action[Context],
    ) -> None:
        """Add a transition to the state machine."""
        self.logger.debug("Adding transition: {%s} + {%s} -> {%s}", from_, event, to)
        self.transitions[(from_, event)] = (to, func)

    def _next(self, state: State, event: Event) -> tuple[State, Action[Context]]:
        """Return the next state and action for a given state and event."""
        try:
            return self.transitions[(state, event)]
        except KeyError as e:
            msg = f"Cannot {event.name} when {state.name}"
            raise InvalidTransitionError(msg) from e

    def handle(self, ctx: Context, state: State, event: Event) -> State:
        """Handle an event and return the next state."""
        self.logger.debug("Handling event: {%s} in state: {%s}", event, state)
        next_state, action = self._next(state, event)
        action(ctx)
        return next_state

    def add(
        self,
        from_: State | Iterable[State],
        event: Event,
        to_state: State,
    ) -> TransitionDecorator[Context]:
        """Add a transition to the state machine.

        Can be used as a decorator to add the action for the transition.
        """
        from_states = (from_,) if isinstance(from_, Enum) else from_

        def decorator(func: Action[Context]) -> Action[Context]:
            for i in from_states:
                self._add(i, event, to_state, func)
            return func

        return decorator
