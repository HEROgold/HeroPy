from herogold.logic.predicate import Predicate, predicate


def test_predicate_call_and_repr() -> None:
    def is_even(n: int) -> bool:
        return n % 2 == 0

    p = Predicate(is_even, 4)
    assert p() is True
    r = repr(p)
    assert "Predicate(" in r
    assert "is_even" in r


def test_predicate_combinators_and_not() -> None:
    p_true = Predicate(lambda: True)
    p_false = Predicate(lambda: False)

    assert (p_true & p_true)() is True
    assert (p_true & p_false)() is False
    assert (p_true | p_false)() is True
    assert (~p_true)() is False

def test_predicate_decorator_only_args() -> None:
    @predicate(5, 6, threshold=10)
    def sum_greater_than(x: int, y: int, threshold: int = 10) -> bool:
        return (x + y) > threshold

    # decorator returns a factory that when called returns a Predicate
    p = sum_greater_than()
    assert isinstance(p, Predicate)
    assert p() is True

def test_predicate_decorator_no_args_accepts_required_arguments() -> None:
    @predicate()
    def requires_x(x: int, y: int = 0) -> bool:
        return x > y

    # decorator with no outer args should still return a factory
    # that accepts the required positional argument(s).
    p = requires_x(2)
    assert isinstance(p, Predicate)
    assert p() is True


def test_predicate_decorator_merges_args_kwargs() -> None:
    @predicate(2)
    def greater_than(x: int, y: int = 0) -> bool:
        return x > y

    # decorator returns a factory that when called returns a Predicate
    p = greater_than(1)
    assert isinstance(p, Predicate)
    # args merged: earlier 2 then 1 -> function receives (2, 1)
    assert p() is True
