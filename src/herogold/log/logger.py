# type: ignore[reportIncompatibleMethodOverride]
"""Custom logger implementation for python 3.14."""
from __future__ import annotations

from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING, _ExcInfoType
from logging import Logger as LoggingLogger
from typing import TYPE_CHECKING, Any, Literal, override

from herogold.sentinel import create_sentinel

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping
    from string.templatelib import Template

__all__ = ["Logger"]

NO_ARG = create_sentinel()
"""Special sentinel value indicating no argument."""


class Logger(LoggingLogger):
    """Custom logger, supporting template string literals."""

    def _interpolate(self, msg: Template) -> Generator[tuple[str, None] | tuple[Literal["%s"], Any]]:
        """Interpolate a Template message into a string and argument counterparts."""
        for part in msg:
            if isinstance(part, str):
                yield part, NO_ARG
            else:
                yield "%s", part.value

    def _build_msg(self, msg: Template) -> tuple[str, list[object]]:
        """Build the final log message string, combined with required arguments properly formatted."""
        parts: list[str] = []
        arguments: list[object] = []
        for part, arg in self._interpolate(msg):
            parts.append(part)
            if arg is not NO_ARG:
                arguments.append(arg)
        return "".join(parts), arguments

    @override
    def debug(
        self,
        msg: Template,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().debug(
            *self._build_msg(msg), exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra,
        )

    @override
    def info(
        self,
        msg: Template,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().info(*self._build_msg(msg), exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra)

    @override
    def warning(
        self,
        msg: Template,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().warning(
            *self._build_msg(msg), exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra,
        )

    @override
    def error(
        self,
        msg: Template,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().error(
            *self._build_msg(msg), exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra,
        )

    @override
    def exception(
        self,
        msg: Template,
        exc_info: _ExcInfoType = True,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().exception(
            *self._build_msg(msg), exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra,
        )

    @override
    def critical(
        self,
        msg: Template,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        return super().critical(
            *self._build_msg(msg), exc_info=exc_info, stack_info=stack_info, stacklevel=stacklevel, extra=extra,
        )

    @override
    def fatal(self, msg: Template) -> None:
        return self.critical(msg)

    @override
    def log(self, level: int, msg: Template) -> None:  # noqa: PLR0911
        super().log(*self._build_msg)
        if level <= CRITICAL: return self.critical(msg)
        if level <= ERROR: return self.error(msg)
        if level <= WARNING: return self.warning(msg)
        if level <= INFO: return self.info(msg)
        if level <= DEBUG: return self.debug(msg)
        if level <= NOTSET: return super().log(0, msg)
        return None
