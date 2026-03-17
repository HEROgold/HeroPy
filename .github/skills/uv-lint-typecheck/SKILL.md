---
name: uv-lint-typecheck
description: "Run Python formatting, linting, tests, and type-checking with uvx. Use when verifying code quality, fixing lint errors, checking type errors, validating a package or the whole repo, or before finishing Python changes. Run uvx ruff format when formatting is needed, then uvx ruff check and uvx ty check; if uvx ty misses expected errors or behaves unreliably, fall back to uvx pyrefly, then uvx pyright. Use uvx pytest to run relevant tests. Never use # type: ignore, # pyright: ignore, noqa, or similar suppression-based fixes unless the user explicitly requests it."
argument-hint: "[target] — optional path to check, such as src/, tests/, or herogold/src/orm"
---

# UV Lint And Typecheck

Enforces a consistent Python formatting, linting, testing, and type-checking workflow based on `uvx` tools.

## When to Use
- Validating Python changes before finishing work
- Formatting Python files after code changes when needed
- Investigating lint or type-check failures
- Running relevant tests after code changes
- Reviewing whether code is safe to merge
- Checking a specific package, module, or the whole repository

## Required Tool Order

Always use this order:

1. `uvx ruff format` when formatting changed Python files or fixing style issues
2. `uvx ruff check`
3. `uvx ty check`
4. `uvx pyrefly check` only if `uvx ty check` appears to miss expected type errors or is otherwise unreliable
5. `uvx pyright` only if `uvx pyrefly check` is unavailable, broken, or also behaves unreliably
6. `uvx pytest` for relevant tests after code changes, if tests are present

Do not replace these with plain `ruff`, `ty`, `pyrefly`, `pytest`, or `pyright` commands unless the user explicitly asks for that.

## Non-Negotiable Rules

- Do not use suppression comments or directives to make errors disappear
- Do not add `# type: ignore`, `# pyright: ignore`, `# noqa`, `# noqa: ...`, `# pylint: disable`, or similar bypasses as a routine fix
- Do not weaken checker configuration just to get a clean run
- Do not remove annotations, delete failing tests, or hide imports to silence diagnostics
- Fix the underlying code issue instead
- If a suppression seems truly necessary, stop and ask the user before adding it

## Default Commands

From the repository root:

```powershell
uvx ruff format .
uvx ruff check .
uvx ty check .
uvx pytest
```

For a narrower target:

```powershell
uvx ruff format <target>
uvx ruff check <target>
uvx ty check <target>
```

For targeted tests:

```powershell
uvx pytest <target>
```

If `ty` misses an error that should be reported:

```powershell
uvx pyrefly check <target>
```

If `pyrefly` is not usable:

```powershell
uvx pyright <target>
```

## How to Decide on Fallbacks

Use `pyrefly` after `ty` when one or more of these is true:
- `ty` reports success but the code still contains an obvious type mismatch
- `ty` crashes, hangs, or produces output that does not match the code under test
- a previously known bad pattern is not flagged by `ty`

Use `pyright` after `pyrefly` when one or more of these is true:
- `uvx pyrefly` is unavailable in the environment
- `pyrefly` crashes or cannot analyze the target
- `pyrefly` also appears to miss the same likely type issue

## Fix Strategy

When issues are found:

1. Fix code, not symptoms
2. Preserve public behavior unless the bug requires a behavior change
3. Re-run `uvx ruff format` if edits changed formatting-sensitive files
4. Rerun the same command that failed
5. Run relevant tests with `uvx pytest`
6. After targeted fixes pass, rerun the broader check if the task warrants it

Acceptable fixes include:
- correcting bad control flow
- narrowing unions properly
- guarding `None`
- refining protocols, overloads, or generics
- improving imports or package structure
- updating tests when behavior intentionally changes

## Completion Checklist

- `uvx ruff format` was run when formatting was needed
- `uvx ruff check` was run on the relevant scope
- `uvx ty check` was run on the relevant scope
- `uvx pyrefly check` was used if `ty` was insufficient
- `uvx pyright` was used if `pyrefly` was insufficient
- `uvx pytest` was run on the relevant scope when tests existed for the change
- no suppression comments or config downgrades were introduced to force success
- final response states which commands were run and whether any fallback checker was needed