from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from herogold import log as log_module
from herogold.log import FileHandler, Logger, StreamHandler, getLogger

SRC = Path(__file__).resolve().parents[1] / "src"


def test_314_logging() -> None:
    """Usage of the custom Logger."""
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


def test_get_logger_returns_same_instance_for_same_name() -> None:
    assert getLogger("issue55.same") is getLogger("issue55.same")


def _messages(caplog: pytest.LogCaptureFixture, name: str) -> list[str]:
    """Messages from one logger, so stray records from other loggers don't matter."""
    return [record.getMessage() for record in caplog.records if record.name == name]


def test_module_logger_record_reaches_root_handler(caplog: pytest.LogCaptureFixture) -> None:
    logger = getLogger("issue55.module")
    count = 3

    logger.warning(t"seen {count} times")

    assert _messages(caplog, "issue55.module") == ["seen 3 times"]


def test_root_logger_is_the_logging_root() -> None:
    assert getLogger() is logging.root


def test_module_level_helpers_log_through_the_herogold_logger(caplog: pytest.LogCaptureFixture) -> None:
    item = "helper"

    log_module.warning(t"from the {item}")

    assert _messages(caplog, "herogold") == ["from the helper"]


def test_mixin_record_is_printed_once_and_reaches_global_log(tmp_path: Path) -> None:
    code = dedent("""        import logging

        from herogold.log import INFO, LoggerMixin, setup

        setup(level=INFO)

        class Issue55Mixin(LoggerMixin):
            pass

        Issue55Mixin().logger.warning("issue55 mixin once")
        print(logging.getLogger("third.party").isEnabledFor(logging.DEBUG))
        """)

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(SRC)},
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stderr.count("issue55 mixin once") == 1
    assert result.stdout.strip() == "False", "LoggerMixin must not lower the root level"
    assert "issue55 mixin once" in (tmp_path / "logs" / "_global.log").read_text()


def test_exception_formats_template_like_other_levels(caplog: pytest.LogCaptureFixture) -> None:
    logger = getLogger("issue55.exception")
    attempt = 2

    try:
        raise ValueError  # noqa: TRY301
    except ValueError:
        logger.exception(t"attempt {attempt} failed")

    assert _messages(caplog, "issue55.exception") == ["attempt 2 failed"]


def test_printf_style_arguments_still_work(caplog: pytest.LogCaptureFixture) -> None:
    getLogger("issue55.printf").warning("loaded %s rows from %s", 3, "users")

    assert _messages(caplog, "issue55.printf") == ["loaded 3 rows from users"]


def test_records_point_at_the_calling_line(caplog: pytest.LogCaptureFixture) -> None:
    getLogger("issue55.caller").warning("where am I")

    [record] = [r for r in caplog.records if r.name == "issue55.caller"]
    assert (record.filename, record.funcName) == ("test_314_loggers.py", "test_records_point_at_the_calling_line")


def test_template_with_extra_arguments_is_rejected() -> None:
    value = 1

    with pytest.raises(TypeError):
        getLogger("issue55.extra").warning(t"value {value}", 5)
