import os
from datetime import UTC, datetime, timedelta

import pytest

from herogold.progress import PreciseProgressBar, ProgressBar


def test_progress_bar_bar_count_clamps_to_range(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_calculate_bar_area(): return 20

    monkeypatch.setattr(ProgressBar, "calculate_bar_area", mock_calculate_bar_area)

    bar = ProgressBar(total=10)
    bar.update(15)
    assert bar.calculate_bar_count(20) == 20

    bar.current = -5
    assert bar.calculate_bar_count(20) == 0


def test_progress_bar_string_representation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("herogold.progress.get_terminal_size", lambda: os.terminal_size((60, 20)))

    bar = ProgressBar(total=10)
    bar.update(5)
    text = str(bar)

    assert text.startswith("Progress:")
    assert bar.start in text
    assert bar.arrow in text
    assert text.endswith(bar.end)


def test_progress_bar_reset_timer() -> None:
    bar = ProgressBar(total=1)
    bar._start_time = datetime.now(tz=UTC) - timedelta(seconds=10) # type: ignore[reportPrivateUsage]

    assert bar.elapsed_time > timedelta(seconds=0)

    bar.reset_timer()
    assert bar.elapsed_time < timedelta(seconds=1)


def test_precise_progress_bar_partial_character(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("herogold.progress.get_terminal_size", lambda: os.terminal_size((60, 20)))

    bar = PreciseProgressBar(total=8)
    bar.update(3.25)

    assert hasattr(bar, "partial_bar")
    assert bar.partial_bar in PreciseProgressBar.partial_bars
    assert bar.partial_bar in str(bar)

    bar.update(8)
    assert bar.partial_bar == ""
