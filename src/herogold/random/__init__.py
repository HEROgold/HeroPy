import random
from collections.abc import Sequence

from herogold.sentinel import MISSING


def recursive_rolls(target: float, rolls: int = 1) -> int:
    """Recursively rolls a random value between 0 and 1, comparing it to the target value."""
    if target < 0 or target > 1:
        msg = "Target must be between 0 and 1."
        raise ValueError(msg)

    total = 0
    if rolls == 0:
        return total

    roll = random.uniform(0, 1)  # noqa: S311

    if roll <= target:
        rolls += 1
        total += 1

    return 1 + recursive_rolls(target, rolls - 1)


def recursive_selection[T](
    items: Sequence[T],
    target: float,
    rolls: int = 1,
    *,
    weights: Sequence[int] = MISSING,
) -> list[T]:
    """Recursively selects items from a sequence based on a target probability."""
    amount = recursive_rolls(target, rolls)
    if amount == 0:
        return []

    if weights is MISSING:
        return random.sample(items, amount)
    return random.sample(items, amount, counts=weights)
