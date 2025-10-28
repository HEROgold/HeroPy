import random
from collections.abc import Sequence

from herogold.sentinel import MISSING


def recursive_rolls(target: float, rolls: int = 1) -> int:
    """Recursively rolls a die with a `target` probability of success.
    Every successful roll increments the total by 1.

    Parameters
    ----------
    :param:`target`: :class:`float`
        The target probability of success. Must be between 0 and 1.
    :param:`rolls`: :class:`int`
        The minimum amount of rolls to try, default is 1.

    """
    if target < 0 or target > 1:
        msg = "Target must be between 0 and 1."
        raise ValueError(msg)

    total = 0
    if rolls == 0:
        return total

    roll = random.uniform(0, 1)

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
    """Selects 'n' number of items from the given sequence based on a target value and optional weights.
    Makes use of recursive_rolls to determine the number of items to select.
    Makes use of random.sample to select items from the sequence.

    Args:
        items (Sequence[T]): The sequence of items to select from.
        target (float): The target probability of success. Must be between 0 and 1.
        rolls (int, optional): The minimum amount of rolls to try, default is 1.
        weights (Sequence[int], optional): The weights associated with each item, higher weights are more likely to appear.

    Returns:
        list[T]: A list of selected items.

    """
    amount = recursive_rolls(target, rolls)
    if amount == 0:
        return []

    if weights is MISSING:
        return random.sample(items, amount)
    return random.sample(items, amount, counts=weights)
