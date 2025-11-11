"""Context manager for creating and managing temporary file copies/backup.

Allows you to change a file, without affecting the original file until the context is exited
successfully.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

temp_dir = Path(mkdtemp())

DIRECTORY_NOT_EMPTY_CODE = 145

class TempFile:
    """Context manager for creating and managing a temporary file copy."""

    def __init__(self, file: Path) -> None:
        """Initialize with the path of the file to be temporarily copied."""
        self.file = file

    def __enter__(self) -> Path:
        """Create a temporary copy of the file and return its path."""
        self.original = self.file
        self.temp = temp_dir / self.original.with_suffix(".tmp").name
        shutil.copy(self.original, self.temp)
        return self.temp

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None | False:
        """On exit, if no exception occurred, replace the original file with the temp file."""
        if exc_type or exc_value or traceback:
            if exc_value:
                exc_value = type(exc_value)(f"{exc_value} (Temporary file: {self.temp})").with_traceback(traceback)
            return False

        new = self.temp.with_stem(f"{self.temp.stem}").with_suffix(self.original.suffix)
        shutil.copy(self.temp, new)
        self.temp.unlink()

        try:
            temp_dir.rmdir()
        except OSError as e:
            # directory is not empty,ignore it.
            if e.winerror == DIRECTORY_NOT_EMPTY_CODE:
                pass
