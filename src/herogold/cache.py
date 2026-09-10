"""A simple cache implementation that uses weak references to allow values to be garbage collected when they are no longer in use."""
from __future__ import annotations

from weakref import ref

from herogold.errors import with_known_exception
from herogold.protocols import Container


class Cache[K, V](Container[K, V]):
    """A simple cache implementation.

    Uses weak references to allow values to be garbage collected.
    """

    def __init__(self, cache: dict[K, ref[V]]) -> None:
        """Initialize the cache."""
        self._cache = cache

    @with_known_exception(AttributeError)
    def __get__(self, instance: K, owner: type[K]) -> V:
        """Get a value from the cache."""
        # Get the weak reference from the cache and dereference it to get the actual value.
        if (result := self._cache.get(instance)) and (r := result()) is not None:
            return r

        # If the weak reference is None, it means the value has been garbage collected.
        del self._cache[instance] # Remove the key from the cache if the value has been garbage collected
        msg = f"{instance} not found in cache"
        raise AttributeError(msg)

    def __set__(self, instance: K, value: V) -> None:
        """Set a value in the cache."""
        self._cache[instance] = ref(value)
