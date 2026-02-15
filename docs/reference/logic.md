# Logic Reference

Composable predicates, actions, and triggers for business logic.

---

## Overview

The [`herogold.logic`](pdoc:herogold.logic) module provides functional building blocks:

- **Predicates** - Composable boolean conditions
- **Actions** - Side-effect wrappers with partial application
- **Triggers** - Condition-action pairs

All components support:
- ✅ Composition with operators
- ✅ Partial application
- ✅ Full type safety

---

## Key Classes

### Predicate

[`Predicate[P]`](pdoc:herogold.logic.Predicate) - Wrapper for boolean functions.

**Creation:**
```python
from herogold.logic import Predicate, predicate

# Direct
is_even = Predicate(lambda x: x % 2 == 0)

# Decorator
@predicate
def is_positive(x: int) -> bool:
    return x > 0
```

**Operators:**
- `p1 & p2` - AND (both must be true)
- `p1 | p2` - OR (either must be true)
- `~p1` - NOT (invert result)

**Methods:**
- [`__call__(*args, **kwargs)`](pdoc:herogold.logic.Predicate.__call__) - Execute predicate

**Example:**
```python
is_valid = is_positive & is_even  # Compose

if is_valid(4):
    print("Valid!")
```

### Action

[`Action[P]`](pdoc:herogold.logic.Action) - Wrapper for side-effect functions.

**Creation:**
```python
from herogold.logic import Action, action

# Direct
log = Action(lambda msg: print(f"[LOG] {msg}"))

# Decorator
@action
def send_email(to: str, subject: str, body: str) -> None:
    print(f"Email to {to}: {subject}")
```

**Partial Application:**
```python
@action
def log_message(message: str, level: str = "INFO") -> None:
    print(f"[{level}] {message}")

# Create specialized actions
log_error = log_message(level="ERROR")
log_debug = log_message(level="DEBUG")

# Use them
log_error("Failed to connect")
log_debug("Query executed")
```

**Methods:**
- [`__call__(*args, **kwargs)`](pdoc:herogold.logic.Action.__call__) - Execute action

### Trigger

[`Trigger[P]`](pdoc:herogold.logic.Trigger) - Executes action when predicate is true.

**Usage:**
```python
from herogold.logic import Trigger

is_error = predicate(lambda code: code >= 400)
send_alert = action(lambda msg: print(f"ALERT: {msg}"))

error_trigger = Trigger(
    predicate=is_error,
    action=send_alert,
)

# Execute
pred_result, action_result = error_trigger(500, "Server error")
# Predicate must be True for action to run
```

**Constructor:**
```python
Trigger(predicate: Predicate[P], action: Action[P])
```

**Methods:**
- [`__call__(*args, **kwargs)`](pdoc:herogold.logic.Trigger.__call__) - Execute trigger

**Returns:** `(predicate_result: bool, action_result: Any)`

---

## Decorators

### @predicate

[`@predicate`](pdoc:herogold.logic.predicate) - Decorator to create predicates.

**Signature:**
```python
@predicate
def my_check(x: int, threshold: int = 0) -> bool:
    return x > threshold

# Creates Predicate that supports:
my_check(5)  # Direct call
my_check(threshold=10)  # Partial application
```

### @action

[`@action`](pdoc:herogold.logic.action) - Decorator to create actions.

**Signature:**
```python
@action
def my_action(value: str, prefix: str = ">") -> None:
    print(f"{prefix} {value}")

# Creates Action that supports:
my_action("hello")  # Direct call
my_action(prefix=">>")  # Partial application
```

---

## Common Patterns

### Validation Chain

```python
@predicate
def has_email(user: dict) -> bool:
    return "email" in user

@predicate
def has_name(user: dict) -> bool:
    return "name" in user

@predicate
def email_valid(user: dict) -> bool:
    return "@" in user.get("email", "")

# Compose validation
is_valid_user = has_email & has_name & email_valid

user = {"email": "test@example.com", "name": "John"}
if is_valid_user(user):
    print("Valid user!")
```

### Partial Predicates

```python
@predicate
def in_range(value: int, min_val: int, max_val: int) -> bool:
    return min_val <= value <= max_val

# Create specialized checks
is_valid_age = in_range(min_val=0, max_val=120)
is_valid_percentage = in_range(min_val=0, max_val=100)

if is_valid_age(25):
    print("Valid age")
```

### Error Handling Pipeline

```python
is_client_error = predicate(lambda code: 400 <= code < 500)
is_server_error = predicate(lambda code: code >= 500)

log_client_error = action(lambda code: print(f"Client error: {code}"))
page_ops = action(lambda code: print(f"URGENT: Server error {code}"))

client_error_trigger = Trigger(is_client_error, log_client_error)
server_error_trigger = Trigger(is_server_error, page_ops)

def handle_http_error(code: int) -> None:
    client_error_trigger(code)
    server_error_trigger(code)
```

### Complex Business Rules

```python
from typing import Dict

@predicate
def is_premium(user: Dict) -> bool:
    return user.get("tier") == "premium"

@predicate
def quota_exceeded(user: Dict) -> bool:
    return user.get("usage", 0) > user.get("quota", 100)

@predicate
def is_trial(user: Dict) -> bool:
    return user.get("trial", False)

# Complex rule
can_access = (is_premium & ~quota_exceeded) | is_trial

user = {"tier": "premium", "usage": 50, "quota": 100}
if can_access(user):
    print("Access granted")
```

---

## Type Safety

All components are generic and preserve type information:

```python
from typing import TypeVar

T = TypeVar('T')

@predicate
def is_type(obj: object, target_type: type[T]) -> bool:
    return isinstance(obj, target_type)

is_string = is_type(target_type=str)
is_int = is_type(target_type=int)

if is_string("hello"):
    print("It's a string!")
```

---

## Performance Notes

- Predicates are lightweight wrappers (minimal overhead)
- Composition creates new predicate instances (not expensive)
- Actions execute immediately when called
- Triggers evaluate predicate before action (short-circuit if false)

---

## See Also

- [Examples: Logic System](../examples/logic.md)
- [Full API](pdoc:herogold.logic)
