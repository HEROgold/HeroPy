from herogold.logic.action import Action
from herogold.logic.predicate import Predicate
from herogold.logic.trigger import DidNotRun, Trigger


def test_trigger_runs_action_when_condition_true() -> None:
    called = {"count": 0}

    def do_stuff() -> str:
        called["count"] += 1
        return "done"

    action = Action(do_stuff)
    condition = Predicate(lambda: True)
    t = Trigger(condition, action)

    result = t()
    assert result == "done"
    assert called["count"] == 1


def test_trigger_returns_sentinel_when_condition_false() -> None:
    def do_nothing() -> int:
        raise RuntimeError("should not run")

    action = Action(do_nothing)
    condition = Predicate(lambda: False)
    t = Trigger(condition, action)

    result = t()
    assert result is DidNotRun
