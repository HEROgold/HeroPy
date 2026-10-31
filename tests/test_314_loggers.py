from __future__ import annotations

import logging
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from herogold import log as log_module
from herogold.log import DEBUG, FileHandler, Handler, Logger, LogRecord, StreamHandler, getLogger

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def test_314_logging() -> None:
    """Usage of the custom Logger."""
    if not sys.version_info >= (3, 14):
        return

    logger = Logger("herogold")
    logger.addHandler(StreamHandler())
    logger.addFilter(FileHandler("herogold.log"))
    logger.setLevel(0)
    world = "world"
    number = 42.159
    item = "something"
    error = "an error message"
    logger.info(t"Hello, {world}!")
    logger.debug(t"This is a debug message with a number: {number}")
    logger.warning(t"This is a warning about {item}.")
    logger.error(t"An error occurred: {error}")
    try:
        # pyrefly: ignore [division-by-zero]
        1 / 0  # noqa: B018
    except ZeroDivisionError:
        logger.exception(t"Caught an exception.")


needs_314 = pytest.mark.skipif(sys.version_info < (3, 14), reason="custom Logger is 3.14+ only")


@needs_314
def test_get_logger_returns_same_instance_for_same_name() -> None:
    assert getLogger("issue55.same") is getLogger("issue55.same")


class _Capture(Handler):
    def __init__(self) -> None:
        super().__init__(level=DEBUG)
        self.messages: list[str] = []

    def emit(self, record: LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.fixture
def root_capture() -> Iterator[_Capture]:
    handler = _Capture()
    logging.root.addHandler(handler)
    yield handler
    logging.root.removeHandler(handler)


@needs_314
def test_module_logger_record_reaches_root_handler(root_capture: _Capture) -> None:
    logger = getLogger("issue55.module")
    count = 3

    logger.warning(t"seen {count} times")

    assert root_capture.messages == ["seen 3 times"]


@needs_314
def test_root_logger_is_the_logging_root_and_accepts_templates(root_capture: _Capture) -> None:
    root = getLogger()
    name = "root"

    root.warning(t"hello from {name}")

    assert root is logging.root
    assert root_capture.messages == ["hello from root"]


@needs_314
def test_module_level_helpers_log_through_the_root(root_capture: _Capture) -> None:
    item = "helper"

    log_module.warning(t"from the {item}")

    assert root_capture.messages == ["from the helper"]


_MIXIN_SCRIPT = """
from herogold.log import LoggerMixin

class Issue55Mixin(LoggerMixin):
    pass

Issue55Mixin().logger.warning("issue55 mixin once")
"""


@needs_314
def test_mixin_record_is_printed_once_and_reaches_global_log(tmp_path: Path) -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", _MIXIN_SCRIPT],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stderr.count("issue55 mixin once") == 1
    assert "issue55 mixin once" in (tmp_path / "logs" / "_global.log").read_text()


@needs_314
def test_exception_formats_template_like_other_levels(root_capture: _Capture) -> None:
    logger = getLogger("issue55.exception")
    attempt = 2

    try:
        raise ValueError  # noqa: TRY301
    except ValueError:
        logger.exception(t"attempt {attempt} failed")

    assert root_capture.messages == ["attempt 2 failed"]


@needs_314
def test_printf_style_arguments_still_work(root_capture: _Capture) -> None:
    getLogger("issue55.printf").warning("loaded %s rows from %s", 3, "users")

    assert root_capture.messages == ["loaded 3 rows from users"]
