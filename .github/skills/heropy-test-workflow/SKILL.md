---
name: heropy-test-workflow
description: 'Generate and verify pytest tests for HeroPy modules. Use when adding tests, fixing failing tests, or validating coverage. Tests always go in the top-level tests/ folder, and the goal is 100% line coverage when practical.'
argument-hint: 'Target module or feature to test; explain any coverage gaps if 100% is not reachable.'
---

# HeroPy Test Workflow

## When to Use
- Add new tests for code under `src/herogold/`
- Fix or extend existing pytest coverage
- Verify behavior changes and prevent regressions
- Measure coverage and explain any missed lines

## Rules
- Put tests in the top-level `tests/` folder.
- Do not create tests under `src/`.
- Prefer small, focused pytest tests that match the repository's existing style.
- Aim for 100% line coverage on the targeted code when practical.
- If 100% line coverage is not reachable, state exactly which lines remain uncovered and why.

## Procedure
1. Inspect the target module and nearby tests to match naming, imports, and assertion style.
2. Identify the public behavior, edge cases, and error paths that matter.
3. Create or update a file under `tests/` with pytest tests for those behaviors.
4. Prefer direct assertions over helpers unless a helper makes the test clearer.
5. Keep tests deterministic and avoid external I/O unless the behavior requires it.
6. Run the targeted tests first, then check coverage for the affected module.
7. If coverage is below 100%, reduce the gap or explain the missing lines and the reason.
8. Validate the final change with the repo's quality checks when relevant: `uvx pytest`, `uvx ruff check`, `uvx ty check`.

## Completion Criteria
- Tests live in `tests/`.
- Behavior is covered for normal, failure, and boundary cases.
- Coverage is reported clearly, with any gaps explained.
- The tests are consistent with the repository's style and tooling.
