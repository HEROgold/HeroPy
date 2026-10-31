"""Tests for the opt-in logging setup in herogold.log (TDD red step)."""

from __future__ import annotations

import importlib
import logging
import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from herogold.log import LoggerMixin, getLogger, log_directory, setup, teardown

SRC_DIR = Path(__file__).resolve().parents[1] / "src"


@pytest.fixture(autouse=True)
def _teardown_after_test():
    """Remove the handlers and root level that setup() installed."""
    yield
    teardown()


def _flush_root_handlers() -> None:
    for handler in logging.getLogger().handlers:
        handler.flush()


def test_import_has_no_side_effects(tmp_path: Path) -> None:
    """Importing herogold.log and herogold.orm changes no root state and creates no logs dir."""
    code = dedent("""\
        import logging, sys
        root = logging.getLogger()
        level = root.level
        handlers = list(root.handlers)
        import herogold.log, herogold.orm
        ok = True
        if root.level != level:
            print('root level changed:', level, '->', root.level)
            ok = False
        if root.handlers != handlers:
            print('root handlers changed:', handlers, '->', root.handlers)
            ok = False
        sys.exit(0 if ok else 1)
        """)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)

    # S603: the command is the test interpreter and a literal code string, not untrusted input.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert not (tmp_path / "logs").exists()


def test_mixin_adds_no_handlers() -> None:
    """Defining a LoggerMixin subclass and reading .logger adds no handlers and changes no levels."""
    root = logging.getLogger()
    level = root.level
    handlers = list(root.handlers)

    class Foo(LoggerMixin):
        pass

    logger = Foo().logger

    assert logger.name.endswith("Foo")
    assert logger.handlers == []
    assert root.level == level
    assert root.handlers == handlers


def test_setup_creates_directory_lazily(tmp_path: Path) -> None:
    """setup() does not create the directory; the first record written does."""
    d = tmp_path / "x"

    setup(d)
    assert not d.exists()

    logging.getLogger("herogold.testlazy").info("hello lazy")
    _flush_root_handlers()

    assert d.exists()
    assert "hello lazy" in (d / "_global.log").read_text()
    assert log_directory() == d


def test_setup_is_idempotent(tmp_path: Path) -> None:
    """Calling setup() twice does not grow the number of root handlers."""
    root = logging.getLogger()

    setup(tmp_path)
    count = len(root.handlers)

    setup(tmp_path)

    assert len(root.handlers) == count


def test_teardown_restores_root(tmp_path: Path) -> None:
    """teardown() restores the root level and handlers from before setup()."""
    root = logging.getLogger()
    level = root.level
    handlers = list(root.handlers)

    setup(tmp_path, level=logging.DEBUG)
    teardown()

    assert root.level == level
    assert root.handlers == handlers
    assert log_directory() is None


def test_per_class_file(tmp_path: Path) -> None:
    """A LoggerMixin subclass writes its DEBUG records to <logger name>.log."""

    class Bar(LoggerMixin):
        pass

    setup(tmp_path)

    logger = Bar().logger
    logger.debug("bar debug")
    _flush_root_handlers()

    expected = tmp_path / f"{logger.name}.log"
    assert expected.exists()
    assert "bar debug" in expected.read_text()


def test_per_class_file_skips_other_loggers(tmp_path: Path) -> None:
    """Loggers not created by LoggerMixin, like third-party ones, get no file of their own."""
    setup(tmp_path)

    logging.getLogger("thirdparty.engine").info("not a class logger")
    _flush_root_handlers()

    assert not (tmp_path / "thirdparty.engine.log").exists()
    assert "not a class logger" in (tmp_path / "_global.log").read_text()


def test_set_log_directory_moves_output(tmp_path: Path) -> None:
    """set_log_directory() re-runs setup() so later records go to the new directory."""
    setup(tmp_path / "a")

    LoggerMixin.set_log_directory(tmp_path / "b")

    assert log_directory() == tmp_path / "b"

    logging.getLogger("herogold.testmove").info("moved")
    _flush_root_handlers()

    assert "moved" in (tmp_path / "b" / "_global.log").read_text()
    assert not (tmp_path / "a").exists()


def test_get_logger_registered() -> None:
    """getLogger() returns the stdlib-registered logger and records propagate to parents."""
    name = "herogold.testreg.child"
    assert getLogger(name) is getLogger(name)
    assert getLogger(name) is logging.getLogger(name)

    class ListHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    parent = logging.getLogger("herogold.testreg")
    child = getLogger(name)
    handler = ListHandler()
    handler.setLevel(logging.DEBUG)
    old_parent_level = parent.level
    old_child_level = child.level

    parent.addHandler(handler)
    parent.setLevel(logging.DEBUG)
    child.setLevel(logging.DEBUG)
    try:
        child.info("propagated")
    finally:
        parent.removeHandler(handler)
        parent.setLevel(old_parent_level)
        child.setLevel(old_child_level)

    assert len(handler.records) == 1
    assert handler.records[0].getMessage() == "propagated"


@pytest.mark.skipif(sys.version_info < (3, 14), reason="custom logger class needs Python 3.14+")
def test_get_logger_custom_class_on_314() -> None:
    """On Python 3.14+, getLogger() returns herogold.log.logger.Logger instances."""
    custom = importlib.import_module("herogold.log.logger")

    assert isinstance(getLogger("herogold.testcls"), custom.Logger)
