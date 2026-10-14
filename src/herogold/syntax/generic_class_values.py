"""Add a generic class that keeps its type arguments available at runtime, including in `__init__`.

Subscripting a subclass with concrete types (`Argument[int]`) returns a cached real subclass whose
`__stored_types__` maps each type parameter name to its argument. `TypeArg` reads one of those back
with a precise static type:

    class Argument[T](GenericClass[T]):
        _type_arg = TypeArg[T]()

        def __init__(self) -> None:
            self.type = self._type_arg or str  # `type[T] | None` to type checkers

    Argument[int]().type  # int
    Argument().type       # str

Plain `typing.Generic` only sets `__orig_class__` on an instance after `__init__` returns, which is
why the types are carried by the class instead.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, ParamSpec, TypeVar, TypeVarTuple, cast, get_args

if TYPE_CHECKING:
    from collections.abc import Mapping


def _is_unresolved(item: object) -> bool:
    """Return whether `item` is, or contains, a type variable."""
    if isinstance(item, TypeVar | ParamSpec | TypeVarTuple):
        return True
    # `list[T]` and the like carry their free type variables in `__parameters__`
    return not isinstance(item, type) and bool(getattr(item, "__parameters__", ()))


def _display_name(item: object) -> str:
    return item.__name__ if isinstance(item, type) else repr(item)


class GenericClass[*Ts]:
    """A generic class whose concrete type arguments are stored in `__stored_types__`.

    Variadic so subclasses can forward any number of parameters: `class Pair[T, J](GenericClass[T, J])`.
    Meant to be subclassed; subscripting `GenericClass` itself is not supported.

    Types are only stored when the class is subscripted explicitly, before it is called:
    - `Argument[int]()` and subclasses like `class IntArgument(Argument[int])` store `{"T": int}`.
    - `Argument()` stores nothing, even when a type checker infers `T` from the arguments or from an
      annotation like `x: Argument[int] = Argument()`.
    - `Argument[int]` is a cached subclass of `Argument`, so `type(Argument[int]())` is not `Argument`,
      and its instances cannot be pickled.
    - Arguments that still contain a type variable (`Argument[T]`, `Argument[list[T]]`) give the normal
      `typing` generic alias and store nothing.

    Values are `object` to type checkers; use `TypeArg` for a precisely typed lookup.
    """

    _registry: ClassVar[dict[tuple[type, tuple[object, ...]], type]] = {}
    __stored_types__: ClassVar[Mapping[str, object]] = MappingProxyType({})
    # Set at runtime by `typing.Generic`; declared so type checkers know it exists
    __parameters__: ClassVar[tuple[TypeVar | ParamSpec | TypeVarTuple, ...]]

    def __class_getitem__(cls, items: object) -> Any:  # noqa: ANN401
        """Return a subclass of `cls` that stores `items` by type parameter name."""
        args = items if isinstance(items, tuple) else (items,)

        # `class Argument[T](GenericClass[T])` or `Argument[list[T]]`: keep the normal generic alias
        if any(_is_unresolved(arg) for arg in args):
            # pyrefly: ignore [missing-attribute]
            return super().__class_getitem__(items)

        names = [param.__name__ for param in cls.__parameters__]
        if len(args) != len(names):
            amount = "many" if len(args) > len(names) else "few"
            msg = f"Too {amount} arguments for {cls.__name__}; actual {len(args)}, expected {len(names)}"
            raise TypeError(msg)

        key = (cls, args)
        if key not in cls._registry:
            suffix = f"[{', '.join(map(_display_name, args))}]"
            cls._registry[key] = type(cls)(
                f"{cls.__name__}{suffix}",
                (cls,),
                {
                    "__module__": cls.__module__,
                    "__qualname__": f"{cls.__qualname__}{suffix}",
                    "__stored_types__": MappingProxyType(dict(zip(names, args, strict=True))),
                    # Fully specialized: subscripting again is an arity error, not a re-specialization
                    "__parameters__": (),
                },
            )
        return cls._registry[key]


class TypeArg[X]:
    """Class-body descriptor that resolves to the concrete type a `GenericClass` subclass was given for `X`.

    Declare one per type parameter you need, passing the parameter itself:

        class Pair[T, J](GenericClass[T, J]):
            second = TypeArg[J]()

        Pair[int, str]().second  # str, typed as `type[J] | None` inside `Pair`

    Resolves to `None` when nothing was stored (see `GenericClass` for when that happens), and when
    the stored value is not a class, such as `int | None` or `Literal["a"]`; read `__stored_types__`
    for the raw value.

    Only valid on `GenericClass` subclasses. Type checkers reject reading it from any other class, and
    at runtime a non-`GenericClass` owner, or anything other than one of the owner's own type
    parameters (`TypeArg()`, `TypeArg[int]()`), raises `TypeError` when the owner class is created.
    """

    name: str

    def __set_name__(self, owner: type[GenericClass[*tuple[Any, ...]]], attr: str) -> None:
        """Remember which of `owner`'s type parameters this descriptor stands for."""
        if not issubclass(owner, GenericClass):
            msg = f"{owner.__name__}.{attr}: TypeArg can only be used on GenericClass subclasses"
            raise TypeError(msg)
        # `TypeArg[T]()` records the alias it was called through on the instance
        orig = getattr(self, "__orig_class__", None)
        param = get_args(orig)[0] if orig is not None else None
        # `__set_name__` runs before `Generic.__init_subclass__`, so `__parameters__` isn't set yet
        if not isinstance(param, TypeVar) or param not in owner.__type_params__:
            msg = f"{owner.__name__}.{attr} must be TypeArg[P]() where P is a type parameter of {owner.__name__}"
            raise TypeError(msg)
        self.name = param.__name__

    def __get__(
        self,
        instance: GenericClass[*tuple[Any, ...]] | None,
        owner: type[GenericClass[*tuple[Any, ...]]],
    ) -> type[X] | None:
        """Return the class stored for this type parameter on `owner`, or `None`."""
        value = owner.__stored_types__.get(self.name)
        return cast("type[X]", value) if isinstance(value, type) else None
