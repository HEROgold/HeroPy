# Logic System Example

## Purpose

Demonstrates the composable logic system:

- [`Predicate`](pdoc:herogold.logic.Predicate) for boolean conditions
- [`Action`](pdoc:herogold.logic.Action) for side effects
- [`Trigger`](pdoc:herogold.logic.Trigger) for condition-action pairs
- Composition with `&`, `|`, `~` operators
- Partial application patterns

## Running

```bash
python examples/logic_demo.py
```

## Predicates

### Basic Usage

```python
from herogold.logic import Predicate, predicate

# Direct creation
is_positive = Predicate(lambda x: x > 0)

# Using decorator
@predicate
def is_even(x: int) -> bool:
    return x % 2 == 0

# Use them
if is_positive(5):
    print("Positive!")

if is_even(4):
    print("Even!")
```

### Composition

```python
# Combine with logical operators
is_positive_even = is_positive & is_even  # AND
is_positive_or_even = is_positive | is_even  # OR
is_negative = ~is_positive  # NOT

# Use composed predicates
if is_positive_even(6):
    print("Positive and even!")
```

### Partial Application

```python
@predicate
def greater_than(x: int, threshold: int) -> bool:
    return x > threshold

# Create specialized predicates
gt_10 = greater_than(threshold=10)
gt_100 = greater_than(threshold=100)

if gt_10(15):  # True
    print("Greater than 10")

if gt_100(15):  # False
    print("This won't print")
```

## Actions

### Basic Usage

```python
from herogold.logic import Action, action

@action
def log_message(message: str, level: str = "INFO") -> None:
    print(f"[{level}] {message}")

@action
def send_notification(user: str, message: str) -> None:
    print(f"Notifying {user}: {message}")

# Execute actions
log_message("System started")
send_notification("admin", "Error detected")
```

### Partial Actions

```python
# Pre-configure actions
log_error = log_message(level="ERROR")
log_debug = log_message(level="DEBUG")

# Use them
log_error("Database connection failed")
log_debug("Query executed successfully")
```

## Triggers

### Combining Predicates and Actions

```python
from herogold.logic import Trigger

# Define components
is_error = Predicate(lambda code: code >= 400)
send_alert = Action(lambda msg: print(f"ALERT: {msg}"))

# Create trigger
error_trigger = Trigger(predicate=is_error, action=send_alert)

# Execute (runs action only if predicate is True)
pred_result, action_result = error_trigger(500)
# Output: ALERT: 500
```

### Complex Example

```python
@predicate
def is_critical_error(code: int) -> bool:
    return code >= 500

@predicate
def is_auth_error(code: int) -> bool:
    return code == 401 or code == 403

@action
def page_admin(message: str) -> None:
    print(f"📟 Paging admin: {message}")

@action
def log_security_event(message: str) -> None:
    print(f"🔒 Security log: {message}")

# Create triggers
critical_trigger = Trigger(
    predicate=is_critical_error,
    action=page_admin,
)

auth_trigger = Trigger(
    predicate=is_auth_error,
    action=log_security_event,
)

# Use in error handler
def handle_error(code: int, message: str) -> None:
    critical_trigger(code, message)
    auth_trigger(code, message)

# Test
handle_error(500, "Database connection lost")
# Output: 📟 Paging admin: Database connection lost

handle_error(401, "Invalid authentication token")
# Output: 🔒 Security log: Invalid authentication token
```

## Real-World Example: Request Validator

```python
from typing import Dict
from herogold.logic import predicate, action, Trigger

@predicate
def has_required_fields(data: Dict, fields: list) -> bool:
    return all(field in data for field in fields)

@predicate
def is_valid_email(email: str) -> bool:
    return "@" in email and "." in email

@action
def reject_request(reason: str) -> None:
    print(f"❌ Request rejected: {reason}")

@action
def accept_request(data: Dict) -> None:
    print(f"✅ Request accepted: {data}")

# Create validation pipeline
required_fields = has_required_fields(fields=["email", "name"])
valid_structure = required_fields & is_valid_email

# Set up triggers
validation_failed = Trigger(
    predicate=~valid_structure,
    action=reject_request,
)

validation_passed = Trigger(
    predicate=valid_structure,
    action=accept_request,
)

# Validate requests
request1 = {"email": "user@example.com", "name": "John"}
request2 = {"email": "invalid", "name": "Jane"}
request3 = {"name": "Bob"}  # Missing email

for req in [request1, request2, request3]:
    validation_passed(req)
    validation_failed(req)
```

## Try Variations

- Create predicates for complex business rules
- Build action pipelines that execute multiple steps
- Implement retry logic with actions
- Use triggers for event-driven systems
- Combine multiple predicates with different operators

## Key Takeaways

- Predicates are composable boolean functions
- Actions encapsulate side effects
- Triggers link conditions to actions
- All components support partial application
- Operators (`&`, `|`, `~`) make composition natural
