"""Custom logger implementation for python 3.14."""

from __future__ import annotations

from logging import Logger as LoggingLogger
from string.templatelib import Interpolation, Template
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping
    from logging import _ExcInfoType

__all__ = ["Logger"]
type SupportsStr = object


class Logger(LoggingLogger):
    """Custom logger, supporting template string literals."""

    @override
    def debug(
        self,
        msg: SupportsStr,
        *args: object,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().debug(
            *self._build_msg(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @override
    def info(
        self,
        msg: SupportsStr,
        *args: object,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().info(
            *self._build_msg(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @override
    def warning(
        self,
        msg: SupportsStr,
        *args: object,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().warning(
            *self._build_msg(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @override
    def error(
        self,
        msg: SupportsStr,
        *args: object,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().error(
            *self._build_msg(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @override
    def exception(
        self,
        msg: SupportsStr,
        *args: object,
        exc_info: _ExcInfoType = True,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().exception(
            *self._build_msg(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @override
    def critical(
        self,
        msg: SupportsStr,
        *args: object,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().critical(
            *self._build_msg(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @override
    def log(
        self,
        level: int,
        msg: SupportsStr,
        *args: object,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().log(
            level,
            *self._build_msg(msg),
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )

    @override
    def getChild(self, suffix: str | None = None) -> Logger:
        """Get a child logger with the given suffix."""
        if self.root is not self:
            suffix = f"{self.name}.{suffix}"
        return Logger(suffix or self.name)

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

    def _build_msg(self, msg: SupportsStr) -> tuple[str, *tuple[object, ...]]:
        """Build the final log message string, combined with required arguments properly formatted."""
        if not isinstance(msg, Template):
            return "%s", msg

        parts: list[str] = []
        arguments: list[object] = []
        for part, arg in self._interpolate(msg):
            parts.append(part)
            arguments.append(arg)
        return "".join(parts), *arguments
