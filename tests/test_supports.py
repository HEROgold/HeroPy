from herogold.supports import (
    SupportsComparison,
    SupportsEq,
    SupportsGE,
    SupportsGT,
    SupportsLE,
    SupportsLT,
    SupportsNe,
)


class DummyGT:
    def __gt__(self, other: object) -> bool:
        return True

class DummyLT:
    def __lt__(self, other: object) -> bool:
        return True

class DummyGE:
    def __ge__(self, other: object) -> bool:
        return True

class DummyLE:
    def __le__(self, other: object) -> bool:
        return True

class DummyEq:
    def __eq__(self, other: object) -> bool:
        return True

class DummyNe:
    def __ne__(self, other: object) -> bool:
        return True

class DummyALL:
    def __gt__(self, other: object) -> bool:
        return True

    def __lt__(self, other: object) -> bool:
        return True

    def __ge__(self, other: object) -> bool:
        return True

    def __le__(self, other: object) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return True

def test_supports_gt_protocol() -> None:
    assert isinstance(DummyGT(), SupportsGT)

def test_supports_lt_protocol() -> None:
    assert isinstance(DummyLT(), SupportsLT)

def test_supports_ge_protocol() -> None:
    assert isinstance(DummyGE(), SupportsGE)

def test_supports_le_protocol() -> None:
    assert isinstance(DummyLE(), SupportsLE)

def test_supports_eq_protocol() -> None:
    assert isinstance(DummyEq(), SupportsEq)

def test_supports_ne_protocol() -> None:
    assert isinstance(DummyNe(), SupportsNe)

def test_supports_comparison_protocol() -> None:
    assert isinstance(DummyALL(), SupportsGT)
    assert isinstance(DummyALL(), SupportsLT)
    assert isinstance(DummyALL(), SupportsGE)
    assert isinstance(DummyALL(), SupportsLE)
    assert isinstance(DummyALL(), SupportsEq)
    assert isinstance(DummyALL(), SupportsNe)
    assert isinstance(DummyALL(), SupportsComparison)

def test_builtin_types() -> None:
    assert isinstance(5, SupportsGT)
    assert isinstance(5, SupportsLT)
    assert isinstance(5, SupportsGE)
    assert isinstance(5, SupportsLE)
    assert isinstance(5, SupportsEq)
    assert isinstance(5, SupportsNe)
    assert isinstance(5, SupportsComparison)

    assert isinstance(3.14, SupportsGT)
    assert isinstance(3.14, SupportsLT)
    assert isinstance(3.14, SupportsGE)
    assert isinstance(3.14, SupportsLE)
    assert isinstance(3.14, SupportsEq)
    assert isinstance(3.14, SupportsNe)
    assert isinstance(3.14, SupportsComparison)

    assert isinstance("hello", SupportsGT)
    assert isinstance("hello", SupportsLT)
    assert isinstance("hello", SupportsGE)
    assert isinstance("hello", SupportsLE)
    assert isinstance("hello", SupportsEq)
    assert isinstance("hello", SupportsNe)
    assert isinstance("hello", SupportsComparison)
