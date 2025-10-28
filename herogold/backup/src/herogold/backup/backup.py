from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

temp_dir = Path(mkdtemp())


class BackupFile:
    def __init__(self, file: Path) -> None:
        self.file = file

    def __enter__(self) -> Path:
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
            if e.winerror == 145:
                pass
