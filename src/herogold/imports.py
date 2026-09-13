"""Simplify custom import for optional dependencies.

```py
try:
    from fastapi import APIRouter, status
except ImportError as e:
    msg = (
        "Failed to import required dependencies for the orm[api] package. "
        "Please ensure that 'api' extra is installed. "
        "You can install them using 'herogold[orm-api]'."
    )
    raise ImportError(msg) from e
```
Would be replace by
```py
with ExtraImportContext(package="herogold", prefix="orm", name="api"):
    from fastapi import APIRouter, HTTPException, Response, status
```
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType


class ExtraImportContext(AbstractContextManager):
    """Context environment for handling extra imports.

    Raises a custom ImportError with a helpful message if the import fails.
    """

    def __init__(self, library: str, module: str, *extras: str) -> None:
        """Initialize the ExtraImportContext."""
        formatted_extras = {",".join(i for i in extras)}
        self.error_message = dedent(
            f"""
            Failed to import required dependencies for the {library}[{module}] module.
            Please ensure that '{formatted_extras}' extra(s) are installed.
            You can install them with '{library}[{formatted_extras}]'.
            """,
        )
        self.library = library
        self.module = module
        self.extras = extras

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Handle the exit of the context for extra imports.

        If an ImportError occurs, raise a custom ImportError with a helpful message.
        """
        if exc_type is ImportError:
            raise ImportError(self.error_message) from exc_value
        return False
