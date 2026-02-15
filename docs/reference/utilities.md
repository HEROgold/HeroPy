# Utilities Reference

Helper functions and common tools.

---

## Overview

The HeroPy utilities module provides:

- **Sentinel values** for missing/undefined state
- **Color constants** for terminal output
- **Logging mixins** for easy logging setup
- **Type checking helpers** for advanced type inspection

---

## Sentinel Values

### MISSING

[`MISSING`](pdoc:herogold.sentinel.MISSING) - Sentinel value for missing/undefined parameters.

**Usage:**
```python
from herogold.sentinel import MISSING

def function(value=MISSING):
    if value is MISSING:
        print("No value provided")
    else:
        print(f"Value: {value}")

function()  # "No value provided"
function(None)  # "Value: None"
function(0)  # "Value: 0"
```

**Why use MISSING?**

Distinguishes between:
- No argument provided (`MISSING`)
- `None` explicitly passed
- Falsy values like `0`, `False`, `""`

**Pattern:**
```python
def get_config(key: str, default=MISSING):
    value = config.get(key)
    
    if value is None:
        if default is MISSING:
            raise ValueError(f"Missing required config: {key}")
        return default
    
    return value
```

---

## Colors

### RAINBOW

[`RAINBOW`](pdoc:herogold.rainbow.RAINBOW) - Tuple of color constants.

**Usage:**
```python
from herogold.rainbow import RAINBOW

for color in RAINBOW:
    print(f"Color: {color}")
```

**Available Colors:**
```python
# Access individual colors
from herogold.colors import RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA

print(f"{RED}Error message{RESET}")
print(f"{GREEN}Success!{RESET}")
```

---

## Logging

### LoggerMixin

[`LoggerMixin`](pdoc:herogold.log.LoggerMixin) - Mixin providing automatic logger setup.

**Usage:**
```python
from herogold.log import LoggerMixin

class MyClass(LoggerMixin):
    def process(self, data):
        self.logger.info("Processing %s", data)
        try:
            result = self._do_work(data)
            self.logger.debug("Result: %s", result)
            return result
        except Exception as e:
            self.logger.exception("Processing failed: %s", e)
            raise
```

**Features:**
- Automatic logger naming (based on class name)
- Logger available as `self.logger`
- Works with inheritance

**Example with Class Methods:**
```python
class DataProcessor(LoggerMixin):
    @classmethod
    def process_batch(cls, items):
        cls.logger.info("Processing %d items", len(items))
        # ...
```

### Logger Formats

Custom formatters available in [`herogold.log.formats`](pdoc:herogold.log.formats):

```python
from herogold.log.formats import DetailedFormatter, SimpleFormatter
import logging

handler = logging.StreamHandler()
handler.setFormatter(DetailedFormatter())

logger = logging.getLogger(__name__)
logger.addHandler(handler)
```

---

## Type Checking

### contains_sub_type

[`contains_sub_type(field, target_type)`](pdoc:herogold.typing.check.contains_sub_type)

Check if a type annotation contains a specific subtype.

**Usage:**
```python
from herogold.typing.check import contains_sub_type
from typing import Optional, Union

# Check if Optional[str] contains str
from pydantic import Field
field = Field(annotation=Optional[str])

if contains_sub_type(field, str):
    print("Field can be a string")
```

**Common Use Cases:**
- Validating type annotations
- Dynamic type checking
- Schema introspection

---

## Progress Tracking

### progress

[`progress(iterable, desc="")`](pdoc:herogold.progress.progress)

Simple progress indicator for iterables.

**Usage:**
```python
from herogold.progress import progress

for item in progress(items, desc="Processing"):
    process(item)
```

---

## Temporary Files

### tempfile helpers

Safe temporary file utilities in [`herogold.tempfile`](pdoc:herogold.tempfile):

```python
from herogold.tempfile import safe_temp_file

with safe_temp_file(suffix=".json") as tmp:
    tmp.write_text('{"data": "value"}')
    # File automatically deleted after context
```

---

## Common Patterns

### Distinguishing Missing Values

```python
from herogold.sentinel import MISSING
from typing import Optional

def update_user(
    user_id: int,
    name: str | None = MISSING,
    email: str | None = MISSING,
) -> None:
    updates = {}
    
    if name is not MISSING:
        updates["name"] = name  # Can be None (delete)
    
    if email is not MISSING:
        updates["email"] = email
    
    # Only update provided fields
    db.update(user_id, **updates)

# Usage
update_user(1, name="John")  # Only update name
update_user(1, name=None)  # Set name to NULL
update_user(1)  # No updates
```

### Colored Console Output

```python
from herogold.colors import RED, GREEN, YELLOW, RESET

def print_status(status: str, message: str) -> None:
    colors = {
        "error": RED,
        "success": GREEN,
        "warning": YELLOW,
    }
    
    color = colors.get(status, "")
    print(f"{color}[{status.upper()}]{RESET} {message}")

print_status("error", "Connection failed")
print_status("success", "Operation completed")
```

### Logging Hierarchy

```python
from herogold.log import LoggerMixin
import logging

class BaseService(LoggerMixin):
    def __init__(self):
        self.logger.setLevel(logging.INFO)

class DatabaseService(BaseService):
    def connect(self):
        self.logger.info("Connecting to database")
        # Logger name: DatabaseService

class CacheService(BaseService):
    def connect(self):
        self.logger.info("Connecting to cache")
        # Logger name: CacheService
```

---

## See Also

- [Full API: herogold.sentinel](pdoc:herogold.sentinel)
- [Full API: herogold.log](pdoc:herogold.log)
- [Full API: herogold.colors](pdoc:herogold.colors)
- [Full API: herogold.typing.check](pdoc:herogold.typing.check)
