"""This module contains the required code to generate a function tree from a given function.
It has support for imported modules, decorators and generators.
"""
import inspect
import re
from typing import Any, Callable

from herogold.sentinel import MISSING


def t4[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)
    return wrapper

@t4
def t1(string: str, number: int) -> None:
    t1(string, number)

def t2(string: str) -> None:
    t1(string, 1)


def t3() -> None:
    t2("2")


calls: dict[str, list[str]] = {}

def generate_call_tree(
    func: Callable[..., Any],
    depth: int=0,
    visited: set[Callable[..., Any]] = MISSING,
) -> None:
    # TODO: doesn't work with imported modules yet
    # TODO: doesn't work with decorators yet
    if visited is MISSING:
        visited = set()

    if func in visited:
        return
    visited.add(func)

    source = inspect.getsource(func)
    called_functions = re.findall(r"\b(\w+)\(\)", source)
    calls[func.__name__] = called_functions[1:] # ignore the first call, which is the current function


    # Recursively process each called function
    for called_func_name in called_functions:
        # Get the function object by name from the globals() dictionary
        called_func = globals().get(called_func_name)
        if called_func and callable(called_func):
            generate_call_tree(called_func, depth + 1, visited)


generate_call_tree(t1)
generate_call_tree(t2)
generate_call_tree(t3)
generate_call_tree(t4)
