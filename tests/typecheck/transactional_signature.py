"""Type-check example: `transactional` keeps parameters and return type. Checked with `ty` and pyrefly, not run by pytest."""

from __future__ import annotations

from typing import assert_type

from herogold.orm import transactional


@transactional
async def add(user: int, name: str = "x") -> bool:
    return bool(user and name)


@transactional(commit_on=(ValueError,), durable=True)
def rename(user: int) -> str:
    return str(user)


async def use() -> None:
    assert_type(await add(1, name="a"), bool)
    assert_type(rename(1), str)
    await add("wrong")  # ty: ignore[invalid-argument-type]  # pyrefly: ignore [bad-argument-type]
    rename(1, 2)  # ty: ignore[too-many-positional-arguments]  # pyrefly: ignore [bad-argument-count]
