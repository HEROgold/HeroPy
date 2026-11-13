from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from herogold.orm import assert_statements, count_statements


def _engine():
    return create_engine("sqlite://", poolclass=StaticPool)


def test_counts_statements_in_block():
    engine = _engine()
    with engine.connect() as conn, count_statements(engine) as counter:
        conn.execute(text("CREATE TABLE t (id INTEGER)"))
        conn.execute(text("INSERT INTO t VALUES (1)"))
        conn.execute(text("SELECT * FROM t"))
    assert counter.count == 3
    assert counter.selects == 1
    assert counter.statements[0] == "CREATE TABLE t (id INTEGER)"
    assert len(counter.statements) == 3


def test_ignores_statements_outside_block():
    engine = _engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        with count_statements(engine) as counter:
            conn.execute(text("SELECT 2"))
        conn.execute(text("SELECT 3"))
    assert counter.count == 1
    assert counter.statements == ["SELECT 2"]


def test_listener_removed_after_exit():
    engine = _engine()
    with engine.connect() as conn:
        with count_statements(engine) as counter:
            pass
        conn.execute(text("SELECT 1"))
    assert counter.count == 0


def test_listener_removed_after_exception():
    engine = _engine()
    counters = []

    def fail_inside_block(conn):
        with count_statements(engine) as counter:
            counters.append(counter)
            conn.execute(text("SELECT 1"))
            msg = "boom"
            raise RuntimeError(msg)

    with engine.connect() as conn:
        with pytest.raises(RuntimeError):
            fail_inside_block(conn)
        conn.execute(text("SELECT 2"))
    assert counters[0].statements == ["SELECT 1"]


def test_assert_statements_passes_on_match():
    engine = _engine()
    with engine.connect() as conn, assert_statements(engine, 2):
        conn.execute(text("SELECT 1"))
        conn.execute(text("SELECT 2"))


def test_assert_statements_message_lists_statements():
    engine = _engine()

    def run_two(conn):
        with assert_statements(engine, 1):
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT 2"))

    with engine.connect() as conn, pytest.raises(AssertionError) as info:
        run_two(conn)
    message = str(info.value)
    assert "expected 1" in message
    assert "got 2" in message
    assert "SELECT 1" in message
    assert "SELECT 2" in message


def test_assert_statements_does_not_mask_block_exception():
    engine = _engine()
    msg = "boom"
    with pytest.raises(RuntimeError), assert_statements(engine, 5):
        raise RuntimeError(msg)
