"""runtime Type checking utilities."""  # noqa: INP001  Avoids `from typing` imports.
from types import NoneType, get_original_bases
from typing import Any, get_args, get_origin

NONE = (None, type(None), NoneType)

def contains_sub_type(needle: object, haystack: object) -> bool:
    """Check if a subtype exists somewhere in the expected type."""
    bases = list(get_original_bases(type(haystack)))

    flat_bases = []
    while bases:
        base = bases.pop()
        if type_args := get_args(base):
            flat_bases.extend(type_args)
        else:
            flat_bases.append(base)
        if get_origin(base):
            bases.extend(get_args(base))

    if needle is None or needle in NONE:
        return any(base in NONE for base in flat_bases)
    if any(base is Any for base in flat_bases):
        return True
    return any(needle is base for base in flat_bases)

# Aliases
has_sub_type = contains_sub_type
is_sub_type = contains_sub_type
