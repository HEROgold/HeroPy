
from types import NoneType
from typing import Any, cast


class InvalidSubTypeError(Exception):
    """Exception raised when a value does not match the expected type."""
    pass

def is_sub_type(cls: object, target: object) -> bool:
    """Validate that a subtype exists in the expected type."""
    orig_bases: tuple[type, ...] | None = getattr(target.__class__, "__orig_bases__", None)

    if not orig_bases:
        msg = "No type information available for validation."
        raise InvalidSubTypeError(msg)

    # Extract type arguments from the generic base
    for base in orig_bases:
        if base is NoneType and cls is None:
            return True # Both are None, considered a match
        if hasattr(base, "__args__"):
            type_args = cast("tuple[type, ...]", base.__args__)
            if type_args:
                for type_arg in type_args:
                    if type_arg in (None, type(None)) and cls is None:
                        return True
                    if type_arg is Any:
                        return True
                    if hasattr(type_arg, "__origin__"):
                        # For parameterized generics, check against the origin type
                        if isinstance(cls, type_arg.__origin__):
                            return True
                    elif isinstance(cls, type_arg):
                        return True
                msg = f"Value {cls} is not any of {type_args}."
                raise InvalidSubTypeError(msg)
    raise RuntimeError("Type validation failed due to unexpected error. Report this with logs and code `DTV-I-001`")
