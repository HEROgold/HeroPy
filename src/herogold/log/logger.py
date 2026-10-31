"""Custom logger implementation for python 3.14."""

from __future__ import annotations

from logging import Logger as LoggingLogger
from logging import RootLogger as LoggingRootLogger
from string.templatelib import Interpolation, Template  # ty: ignore[unresolved-import]  # 3.14+ only, guarded in __init__
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping
    from logging import _ExcInfoType

__all__ = ["Logger", "RootLogger"]


class Logger(LoggingLogger):
    """Custom logger, supporting template string literals."""

    @override
    def _log(
        self,
        level: int,
        msg: object,
        args: tuple[object, ...] | Mapping[str, object],
        exc_info: _ExcInfoType | None = None,
        extra: Mapping[str, object] | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
    ) -> None:
        # Every public logging method ends up here, so templates are handled once.
        if isinstance(msg, Template):
            if args:
                error = "a template message takes no extra arguments"
                raise TypeError(error)
            msg, *template_args = self._build_msg(msg)
            args = tuple(template_args)
        # Skip this frame, so records point at the caller instead of this file.
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel + 1)

    def _interpolate(self, msg: Template) -> Generator[tuple[str, Any]]:
        """Interpolate a Template message into a string and argument counterparts."""
        for part in msg:
            match part:
                case str():
                    yield "%s", part
                case Interpolation(value=float()):
                    yield "%f", part.value
                case Interpolation(value=int()):
                    yield "%d", part.value
                case Interpolation(value=bool()):
                    yield "%b", part.value
                case _:
                    yield "%s", part.value

    def _build_msg(self, msg: Template) -> tuple[str, *tuple[object, ...]]:
        """Build the final log message string, combined with required arguments properly formatted."""
        parts: list[str] = []
        arguments: list[object] = []
        for part, arg in self._interpolate(msg):
            parts.append(part)
            arguments.append(arg)
        return "".join(parts), *arguments


class RootLogger(Logger, LoggingRootLogger):
    """Root logger, supporting template string literals."""
