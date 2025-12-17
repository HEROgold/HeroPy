
from types import NoneType, get_original_bases
from typing import Any, get_args, get_origin


class InvalidSubTypeError(Exception):
    """Exception raised when a value does not match the expected type."""
    pass

# Given: Haystack[TypeArg1[X], TypeArg2[Y]]
# Contains:
# orig_bases = TypeArg1[X], TypeArg2[Y]
# type_args = X or Y (depending on which base we're looking at)


# TODO: rename is_sub_type to something that's more accurate
def is_sub_type(needle: object, haystack: object) -> bool:
    """Validate that a subtype exists in the expected type."""
    orig_bases = get_original_bases(type(haystack))

    if not orig_bases:
        msg = "No type information available for validation."
        raise InvalidSubTypeError(msg)

    # Extract type arguments from the generic base
    for base in orig_bases:
        if base is NoneType and needle is None:
            return True # Both are None, considered a match
        if type_args := get_args(base):
            for type_arg in type_args:
                if type_arg in (None, type(None)) and needle is None:
                    return True
                if type_arg is Any:
                    return True
                if needle is type_arg:
                    return True
                if origin := get_origin(type_arg):
                    # Handle cases like Container[int] where needle is of type Container
                    # TODO: De we remove this check? as Container is not a subtype of Container[int]
                    # only int is a subtype of Container[int]
                    return isinstance(needle, origin)
                return is_sub_type(needle, type_arg)
            msg = f"Value {needle} is not any of {type_args}."
            raise InvalidSubTypeError(msg)
    raise RuntimeError("Type validation failed due to unexpected error. Report this with logs and code `DTV-I-001`")
