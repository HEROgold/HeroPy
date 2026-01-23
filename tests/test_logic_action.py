from herogold.logic.action import Action, action


def test_action_callable_returns_value() -> None:
    def greet() -> str:
        return "hello"

    act = Action(greet)
    assert callable(act)
    assert act() == "hello"


def test_action_decorator_replaces_function_with_action() -> None:
    @action
    def add() -> int:
        return 3 + 4

    # When used as a decorator, the name is replaced by an Action instance
    assert isinstance(add, Action)
    assert add() == 7
