"""The enforce_types wrapper is supposed to enforce any args to match its annotated type.

The overhead is quite big, with simple functions, can ~double the runtime, at 100_000 iterations.
"""
from __future__ import annotations

import asyncio
import inspect
import random
import time
import types
import typing
from asyncio import iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    ParamSpec,
    TypeVar,
    get_type_hints,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

# Generic type variables used for typing the wrapper signatures
F = TypeVar("F")
P = ParamSpec("P")


def args_check(func: Callable[..., Any]) -> Literal[True]:
    """Check if all arguments are type hinted and return True, if it isn't raises TypeError.

    Args:
        func (FunctionType): The function to check

    Raises:
        TypeError: Error that gets raised when annotations are missing

    Returns:
        bool: True

    """
    spec = inspect.getfullargspec(func)
    for arg in [*spec.args, "return"]:
        if arg not in spec.annotations:
            msg = f"Missing type annotation for {arg}"
            raise TypeError(msg)
    return True


def check_annotation(arg: Any, annotation: type | types.UnionType) -> None:  # noqa: ANN401
    """Check if a argument is of a given type.

    Args:
        arg: The argument to check
        annotation: The type to check for

    Raises:
        TypeError: If the type doesn't match, telling which type to expect

    """
    if annotation in [Any]:
        return

    # The wrapper will provide param/function context when calling
    # check_annotation through kwargs (fast-path: avoid getting them here).

    # Handle typing.Union and PEP 604 (X | Y)
    if getattr(annotation, "__origin__", None) is typing.Union or isinstance(annotation, types.UnionType):
        union_args = getattr(annotation, "__args__", None) or getattr(annotation, "__union_args__", None) or ()
        for member in union_args:
            check_annotation(arg, member)
        msg = f"Expected one of {union_args} but got {type(arg)}"
        raise TypeError(msg)

    # Support parameterized generics like list[int] by checking the origin
    origin = getattr(annotation, "__origin__", None)
    if origin is not None:
        if not inspect.isclass(origin):
            msg = f"Expected a class but got {type(annotation)}"
            raise TypeError(msg)
        if not isinstance(arg, origin):
            msg = f"Expected {origin} but got {type(arg)}"
            raise TypeError(msg)
        return

    if not inspect.isclass(annotation):
        msg = f"Expected a class but got {type(annotation)}"
        raise TypeError(msg)
    if not isinstance(arg, annotation):
        msg = f"Expected {annotation} but got {type(arg)}"
        raise TypeError(msg)


def type_check(args: Sequence[Any] | dict[str, Any], annotations: dict[str, type]) -> Literal[True]:
    """Check if arguments are of a annotated type.

    Args:
        args: The argument to check
        annotations: The type to check for

    Raises:
        TypeError: If the type doesn't match, telling which type to expect

    Returns:
        bool: True

    """
    if isinstance(args, dict):
        # args is a mapping of name -> value; check each value against the
        # corresponding annotation for that parameter name.
        for name, value in args.items():
            annotation = annotations.get(name)
            # If annotation is missing this will raise in check_annotation.
            check_annotation(value, annotation)  # type: ignore[arg-type]
    else:
        # For sequences (positional args) iterate over positional parameter
        # annotations only (skip the special 'return' annotation if present).
        param_annotations = [v for k, v in annotations.items() if k != "return"]
        for value, annotation in zip(args, param_annotations):
            check_annotation(value, annotation)
    return True


def enforce_types(func: Callable[..., Any]) -> Callable[..., Any]:
    """Enforce type checking for a function.

    This makes sure that the decorated function needs type hinting.
    Also forces passed arguments to be of that type.
    Uses a cache to store the results of the function, to avoid rechecking the same arguments.

    Raises:
        TypeError: If the type doesn't match, telling which type to expect, or when type hinting is not present

    Args:
        func (FunctionType): The function to check

    """
    # Resolve and validate annotations once at decoration time to avoid
    # repeated work per-call.
    sig = inspect.signature(func)
    resolved_annotations = get_type_hints(func)

    # Ensure all parameters are annotated (mirror previous behavior).
    for name in sig.parameters:
        if name not in resolved_annotations and name != "self":
            msg = f"Missing type annotation for parameter '{name}' in {func.__qualname__}"
            raise TypeError(msg)
    if "return" not in resolved_annotations:
        msg = f"Missing return type annotation for {func.__qualname__}"
        raise TypeError(msg)

    # Function location for clearer error messages
    func_file = getattr(func, "__code__", None) and func.__code__.co_filename
    func_line = getattr(func, "__code__", None) and func.__code__.co_firstlineno

    # Small LRU-like cache keyed by argument types to avoid repeating checks
    from collections import OrderedDict

    cache: OrderedDict[tuple[tuple[str, type], ...], bool] = OrderedDict()
    CACHE_MAX = 2048

    def make_key(bound_args: dict[str, Any]) -> tuple[tuple[str, type], ...]:
        return tuple((name, type(value)) for name, value in bound_args.items()) # pyright: ignore[reportUnknownArgumentType]

    def raise_with_context(err: str, param: str) -> None:
        location = f"{func_file}:{func_line}" if func_file and func_line else "<unknown>"
        # Try to find the caller location (first stack frame outside this module)
        caller_info = None
        try:
            for frame in inspect.stack()[2:]:
                if frame.filename != __file__:
                    caller_info = f"{frame.filename}:{frame.lineno}"
                    break
        except Exception:
            caller_info = None

        if caller_info:
            msg = (
                f"Type error in {func.__qualname__} defined at {location} "
                f"(call site: {caller_info}) -> parameter '{param}': {err}"
            )
        else:
            msg = f"Type error in {func.__qualname__} at {location} -> parameter '{param}': {err}"
        raise TypeError(msg)

    async def async_wrapper(*args: Any, **kwargs: Any):
        bound = sig.bind(*args, **kwargs)
        key = make_key(bound.arguments)
        if key in cache:
            cache.move_to_end(key)
            return await func(*args, **kwargs)

        # Validate each bound argument against its annotation
        for name, value in bound.arguments.items():
            annotation = resolved_annotations.get(name)
            try:
                check_annotation(value, annotation) # pyright: ignore[reportArgumentType]
            except TypeError as exc:
                raise_with_context(str(exc), name)

        # insert into cache
        cache[key] = True
        if len(cache) > CACHE_MAX:
            cache.popitem(last=False)

        return await func(*args, **kwargs)

    def wrapper(*args: Any, **kwargs: Any):
        bound = sig.bind(*args, **kwargs)
        key = make_key(bound.arguments)
        if key in cache:
            cache.move_to_end(key)
            return func(*args, **kwargs)

        for name, value in bound.arguments.items():
            annotation = resolved_annotations.get(name)
            try:
                check_annotation(value, annotation) # pyright: ignore[reportArgumentType]
            except TypeError as exc:
                raise_with_context(str(exc), name)

        cache[key] = True
        if len(cache) > CACHE_MAX:
            cache.popitem(last=False)

        return func(*args, **kwargs)

    if iscoroutinefunction(func):
        return async_wrapper  # type: ignore[reportReturnType]
    return wrapper  # type: ignore[reportReturnType]


def test_collections() -> None:
    @enforce_types
    def collections(a: list[int]) -> bool:
        return True
    def collections_nowrap(a: list[int]) -> bool:
        return True

    # measure non-wrapped
    start = time.perf_counter()
    for _ in range(COLLECTION_COUNT):
        assert collections_nowrap([1, 2, 3]) is True
    nowrap_duration = time.perf_counter() - start

    # Re-measure wrapped to get comparable numbers (this reruns the wrapped loop;
    # acceptable for a simple benchmark in this test function).
    start_wrapped = time.perf_counter()
    for _ in range(COLLECTION_COUNT):
        assert collections([1, 2, 3]) is True
    wrapped_duration = time.perf_counter() - start_wrapped

    diff = wrapped_duration - nowrap_duration
    ratio = wrapped_duration / nowrap_duration if nowrap_duration else float("inf")
    print(  # noqa: T201
        f"collections: wrapped={wrapped_duration:.6f}s, nowrap={nowrap_duration:.6f}s, "
        f"diff={diff:.6f}s, ratio={ratio:.2f}",
    )



def test_simple() -> None:
    @enforce_types
    def test(a: int, b: str) -> bool:
        return True

    def test_nowrap(a: Any, b: Any) -> bool:
        return True

    # measure wrapped
    start = time.perf_counter()
    for _ in range(test_count):
        assert test(random.randint(0, 10), b=random.choice(letters)) is True
    wrapped_duration = time.perf_counter() - start

    # measure non-wrapped
    start = time.perf_counter()
    for _ in range(test_count):
        assert test_nowrap(random.randint(0, 10), b=random.choice(letters)) is True
    nowrap_duration = time.perf_counter() - start

    diff = wrapped_duration - nowrap_duration
    ratio = wrapped_duration / nowrap_duration if nowrap_duration else float("inf")
    print(  # noqa: T201
        f"test_simple: wrapped={wrapped_duration:.6f}s, nowrap={nowrap_duration:.6f}s, "
        f"diff={diff:.6f}s, ratio={ratio:.2f}",
    )


async def async_test_simple() -> None:
    @enforce_types
    async def async_test(a: int, b: str) -> bool:
        return True

    async def async_test_nowrap(a: Any, b: Any) -> bool:
        return True

    # measure wrapped
    start = time.perf_counter()
    for _ in range(test_count):
        assert await async_test(random.randint(0, 10), b=random.choice(letters)) is True
    wrapped_duration = time.perf_counter() - start

    # measure non-wrapped
    start = time.perf_counter()
    for _ in range(test_count):
        assert await async_test_nowrap(random.randint(0, 10), b=random.choice(letters)) is True
    nowrap_duration = time.perf_counter() - start

    diff = wrapped_duration - nowrap_duration
    ratio = wrapped_duration / nowrap_duration if nowrap_duration else float("inf")
    print(  # noqa: T201
        f"test_simple_async: wrapped={wrapped_duration:.6f}s, nowrap={nowrap_duration:.6f}s, "
        f"diff={diff:.6f}s, ratio={ratio:.2f}",
    )

    # sanity call
    start = time.perf_counter()
    for _ in range(test_count):
        assert await async_test(0, b="a") is True
    sanity_duration = time.perf_counter() - start
    print(  # noqa: T201
        f"test_simple_async (sanity calls): duration={sanity_duration:.6f}s",
    )


async def async_test_collections() -> None:
    @enforce_types
    def collections(a: list[int]) -> bool:
        return True

    def collections_nowrap(a: list[int]) -> bool:
        return True

    start = time.perf_counter()
    for _ in range(COLLECTION_COUNT):
        assert collections([1, 2, 3]) is True
    wrapped_duration = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(COLLECTION_COUNT):
        assert collections_nowrap([1, 2, 3]) is True
    nowrap_duration = time.perf_counter() - start

    diff = wrapped_duration - nowrap_duration
    ratio = wrapped_duration / nowrap_duration if nowrap_duration else float("inf")
    print(  # noqa: T201
        f"async_test_collections: wrapped={wrapped_duration:.6f}s, nowrap={nowrap_duration:.6f}s, "
        f"diff={diff:.6f}s, ratio={ratio:.2f}",
    )




def main() -> None:
    test_simple()
    test_collections()


async def main_async() -> None:
    await async_test_simple()
    await async_test_collections()


if __name__ == "__main__":
    test_count = 100_000
    COLLECTION_COUNT = 100_000
    letters = "abcdefghijklmnopqrstuvwxyz"

    test_simple()
    asyncio.run(main_async())
