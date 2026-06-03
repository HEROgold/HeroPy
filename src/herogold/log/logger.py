# type: ignore[reportIncompatibleMethodOverride]
"""Custom logger implementation for python 3.14."""

from __future__ import annotations

from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING
from logging import Logger as LoggingLogger
from typing import TYPE_CHECKING, Any, Literal, override

from herogold.log import FileHandler, StreamHandler
from herogold.sentinel import create_sentinel

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping
    from logging import _ExcInfoType
    from string.templatelib import Template

__all__ = ["Logger"]

NO_ARG = create_sentinel()
"""Special sentinel value indicating no argument."""


class Logger(LoggingLogger):
    """Custom logger, supporting template string literals."""

    def _interpolate(self, msg: Template) -> Generator[tuple[str, None] | tuple[Literal["%s"], Any]]:
        """Interpolate a Template message into a string and argument counterparts."""
        for part in msg:
            match part:
                case str():
                    yield part, NO_ARG
                case float():
                    yield "%f", part.value
                case int():
                    yield "%d", part.value
                case bool():
                    yield "%b", part.value
                case _:
                    yield "%s", part.value

    def _build_msg(self, msg: Template) -> tuple[str, *tuple[object, ...]]:
        """Build the final log message string, combined with required arguments properly formatted."""
        parts: list[str] = []
        arguments: list[object] = []
        for part, arg in self._interpolate(msg):
            parts.append(part)
            if arg is not NO_ARG:
                arguments.append(arg)
        return "".join(parts), *arguments

    @override
    def debug(
        self,
        msg: Template,
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
        msg: Template,
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
        msg: Template,
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
        msg: Template,
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
        msg: Template,
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
        msg: Template,
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
    def log(  # noqa: PLR0911
        self,
        level: int,
        msg: Template,
        *args: object,
        exc_info: _ExcInfoType | None = None,
        stack_info: bool = False,
        stacklevel: int = 1,
        extra: Mapping[str, object] | None = None,
    ) -> None:
        # One liners are cleaner here. Even though they violate pep8, they are more readable in this case.
        # fmt: off
        if level <= CRITICAL: return self.critical(msg, *args)
        if level <= ERROR: return self.error(msg, *args)
        if level <= WARNING: return self.warning(msg, *args)
        if level <= INFO: return self.info(msg, *args)
        if level <= DEBUG: return self.debug(msg, *args)
        if level <= NOTSET: return super().log(0, *self._build_msg(msg))
        return None
        # fmt: on

def main() -> None:
    """Usage of the custom Logger."""
    logger = Logger("herogold")
    logger.addHandler(StreamHandler())
    logger.addFilter(FileHandler("herogold.log"))
    world = "world"
    number = 42.159
    item = "something"
    error = "an error message"
    logger.info(t"Hello, {world}!")
    logger.debug(t"This is a debug message with a number: {number}")
    logger.warning(t"This is a warning about {item}.")
    logger.error(t"An error occurred: {error}")
    try:
        1 / 0  # noqa: B018
    except ZeroDivisionError as exception:
        logger.exception(t"Caught an exception: {exception}.")


if __name__ == "__main__":
    main()
