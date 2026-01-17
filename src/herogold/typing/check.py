"""runtime Type checking utilities."""
from types import NoneType, get_original_bases
from typing import Any, get_args, get_origin

from typing_extensions import deprecated  # Remove dependency when minimum Python version is 3.12

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


@deprecated("Use 'contains_sub_type' or 'has_sub_type' instead. Removed in 2.0")
def is_sub_type(needle: object, haystack: object) -> bool:  # noqa: D103
    return contains_sub_type(needle, haystack)
