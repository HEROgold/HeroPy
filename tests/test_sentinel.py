from herogold.sentinel import MISSING, create_sentinel

def test_missing_is_falsy_and_unique() -> None:
    assert not MISSING
    assert bool(MISSING) is False
    assert (MISSING == object()) is False
    assert (MISSING != object()) is False
    assert (MISSING == MISSING) is False
    assert (MISSING != MISSING) is False
    assert repr(MISSING) == "MISSING"
    assert hash(MISSING) == 0

    # Attribute interaction should never raise and always yield None.
    assert getattr(MISSING, "any_attribute") is None

    fresh = create_sentinel()
    assert fresh is not MISSING
    assert not fresh
    assert (fresh == MISSING) is False
    assert (fresh != MISSING) is False
