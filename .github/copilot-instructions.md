Copilot instructions for this repository
=====================================

Primary goal
------------
Keep a single namespace package `herogold` which contains optional subpackages
(`herogold.sentinel`, `herogold.color`, `herogold.log`, etc.). Subpackages
are small utilities and boilerplate helpers — each lives under a per-package
`src/herogold/<pkg>` layout so that after installation the import path is
`from herogold.<pkg> import ...`.

Python version and features
---------------------------
- Prefer the Python interpreter indicated by a `.python-version` file in the
  subpackage root. If that file is missing, use the latest available version, and us the tool `uv` to set it. (uv python pin <version>)
- Use modern, stable language features appropriate for the target Python version:
  - builtin generics (e.g. `list[int]`, `dict[str, str]`) for typing
  - `def[T](arg1: T) -> T:` style generics
  - `match` / `case` (structural pattern matching) where it improves clarity or adds functionality
  - concise `f`-strings and clear, explicit `__repr__` for debugging
  - `dataclasses`, `typing.Protocol`, `TypedDict`, `Annotated` where helpful
  - prefer `pathlib.Path`, `importlib`, and high-level stdlib APIs

Packaging and layout rules
-------------------------
- Source layout: package code must live under `src/herogold/<pkg>/` (not
  `src/<pkg>`). This ensures installed imports are `herogold.<pkg>`.
- Each subpackage should include a minimal `__init__.py` and public API
  surface (use `__all__` when helpful). Also add small README.md files in
  subpackage folders describing purpose and a tiny usage example.
- Do NOT create compatibility shims at the top-level (no `import sentinel ->
  herogold.sentinel` shims). We prefer the canonical `herogold.<pkg>` import.
- Keep per-package `pyproject.toml` metadata accurate. If you change
  package layout, update workspace mappings (`[tool.uv.sources]` and
  `pyproject` extras) accordingly.

Coding style and quality
------------------------
- Follow the repository's formatter/linter settings (Black, ruff) if present
  in `pyproject.toml` or `ruff.toml`. Use type annotations liberally and keep functions small
  and testable.
- Add or update unit tests (pytest) for any new behavior. Put tests under
  `tests/` or inside each package's `tests/` folder. Use small, fast tests.
- Always use typehinting. use `ruff check` and `ty check` to confirm these cases.
  `ty check` is alpha, so just to be sure, also use `mypy`

When generating code
--------------------
- Produce complete, runnable artifacts: module files, a minimal README, and
  a couple of tests. If adding CLI entry points, wire them in `pyproject.toml`.
- use tools and cli commands (like `ruff`, `uv`, etc) to create these where possible
- Avoid adding external dependencies unless explicitly requested. If a
  dependency is required, update the appropriate package `pyproject.toml`
- add new packages to the workspace configuration in the root `pyproject.toml`

Safety and network
------------------
- Do not include secrets or make remote network calls in generated code.

Workflows and CI/CD
----------------------
- use existing workflows and CI/CD patterns in `.github/workflows/` and `.github/example-workflows/`
- `.github/example-workflows/` contains reusable examples and should be referenced first when creating new workflows
- use #fetch https://docs.astral.sh/uv/guides/integration/github over python actions
- make sure workflows runs parallel jobs where possible to speed up feedback loops
- call and reuse existing workflows where possible
- cache and use results of other workflows to avoid redundant work if it provides value

Examples
--------
- Import sentinel sentinel value:
  from herogold.sentinel import MISSING
- Import rainbow
  from herogold.rainbow import RAINBOW
- Import logging helpers:
  from herogold.log import LoggerMixin

If anything is ambiguous, prefer small, conservative changes and ask for
clarification before large refactors.
