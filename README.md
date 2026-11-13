# herogold

A single package containing personal utilities.

Upgrading from herogold 6.x? See the [7.0.0 migration note](docs/migrations/7.0.0.md).

## Python 3.15

Source: [What's new in Python 3.15](https://docs.python.org/3.15/whatsnew/3.15.html). The package supports Python 3.12 and newer, so 3.15 syntax cannot appear in any module that must import on 3.12.

### Usable now

These work without raising the minimum Python version.

- PEP 810 lazy imports, through the `__lazy_modules__` marker. Older interpreters ignore the list. The `lazy-fix` tool (`[tool.lazy-fix]` in `pyproject.toml`, CI workflow `lazy-imports.yml`) maintains it.
- PEP 686, UTF-8 as the default encoding. Passing an explicit `encoding=` to `open()` and similar calls behaves the same on every version.
- PEP 661 `sentinel`, PEP 814 `frozendict` and other new stdlib APIs, behind `herogold.compat.require_python` or `@requires_python((3, 15))`. `herogold.sentinel` already checks the version.
- PEP 747 `TypeForm`, PEP 728 `TypedDict` extra items and PEP 800 disjoint bases through `typing_extensions`, once it ships them.
- PEP 799 `profiling` package and the Tachyon sampling profiler, as development tools on a 3.15 interpreter.

### Blocked until the minimum is 3.15

These are syntax, so a 3.12 interpreter raises `SyntaxError` before any guard runs.

- PEP 810 `lazy import` and `lazy from ... import`. Until then, `__lazy_modules__` stands in.
- PEP 798 unpacking in comprehensions, such as `[*xs for xs in groups]`.

### Python version policy

The minimum is the oldest CPython that the code can run on. `.github/workflows/test.yml` tests every supported version, and `.github/workflows/update-python-matrix.yml` opens a pull request when the list changes, using [HEROgold/update-python-matrix](https://github.com/HEROgold/update-python-matrix).
