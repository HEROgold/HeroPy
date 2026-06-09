"""A simple cache implementation that uses weak references to allow values to be garbage collected when they are no longer in use."""
from __future__ import annotations

from weakref import ref

from herogold.errors import with_known_exception
from herogold.protocols import Container


class Cache[K, V](Container[K, V]):
    """A simple cache implementation that uses weak references to allow values to be garbage collected when they are no longer in use."""

    def __init__(self, cache: dict[K, ref[V]]) -> None:
        """Initialize the cache."""
        self._cache = cache

    @with_known_exception(AttributeError)
    def __get__(self, instance: K, owner: type[K]) -> V | None:
        """Get a value from the cache."""
        result = self._cache.get(instance)
        if not result:
            msg = f"{instance} not found in cache"
            raise AttributeError(msg)
        return result()

    def __set__(self, instance: K, value: V) -> None:
        """Set a value in the cache."""
        self._cache[instance] = ref(value)
