from typing import Any

import pytest

import herogold.random as random_module


def test_recursive_rolls_rejects_out_of_range_target() -> None:
    with pytest.raises(ValueError):
        random_module.recursive_rolls(-0.1)
    with pytest.raises(ValueError):
        random_module.recursive_rolls(1.1)


def test_recursive_rolls_counts_expected_successes(monkeypatch: pytest.MonkeyPatch) -> None:
    values = iter([0.25, 0.8])

    def fake_uniform(_: float, __: float) -> float:
        try:
            return next(values)
        except StopIteration:
            return 1.0

    monkeypatch.setattr(random_module.random, "uniform", fake_uniform)

    assert random_module.recursive_rolls(0.5, rolls=1) == 2


def test_recursive_selection_without_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_recursive_rolls(target: float, rolls: int = 1) -> int: return 2
    monkeypatch.setattr(random_module, "recursive_rolls", mock_recursive_rolls)

    captured: dict[str, Any] = {}

    def fake_sample(items: list[int], count: int, *, counts: Any | None = None) -> list[int]:
        captured["items"] = items
        captured["count"] = count
        captured["counts"] = counts
        return list(items)[:count]

    monkeypatch.setattr(random_module.random, "sample", fake_sample)

    population = [1, 2, 3, 4]
    result = random_module.recursive_selection(population, target=0.5)

    assert result == [1, 2]
    assert captured["counts"] is None


def test_recursive_selection_with_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_recursive_rolls(target: float, rolls: int = 1) -> int: return 3
    monkeypatch.setattr(random_module, "recursive_rolls", mock_recursive_rolls)

    captured: dict[str, Any] = {}

    def fake_sample(items: list[int], count: int, *, counts: Any | None = None) -> list[int]:
        captured["items"] = items
        captured["count"] = count
        captured["counts"] = counts
        return list(items)[:count]

    monkeypatch.setattr(random_module.random, "sample", fake_sample)

    population = [1, 2, 3, 4]
    weights = [1, 1, 1, 1]
    result = random_module.recursive_selection(population, target=0.5, weights=weights)

    assert result == [1, 2, 3]
    assert captured["counts"] == weights
