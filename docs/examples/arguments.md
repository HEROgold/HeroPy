# Argument Parsing Example ([`arguments.py`](https://github.com/HEROgold/HeroPy/blob/master/examples/arguments.py))

## Purpose

Demonstrates the foundational usage of HeroPy's argument parsing system:

- Setting up [`Argument`](pdoc:herogold.argparse.Argument) descriptors
- Different argument types (int, string, bool)
- Boolean flags with `--flag` / `--no-flag` pattern
- Integration with argparse [`Namespace`]

## Running

```bash
python examples/arguments.py --help
python examples/arguments.py --environment prod --retries 5 --dry-run
python examples/arguments.py --no-dry-run
```

## Code Summary

[`examples/arguments.py`](https://github.com/HEROgold/HeroPy/blob/master/examples/arguments.py) defines `DeployOptions` namespace with:

- `environment`: string argument with default "dev"
- `retries`: integer argument with default 2
- `dry_run`: boolean flag supporting `--dry-run` and `--no-dry-run`

## Example Output

```text
Preparing deployment: env=prod retries=5 dry_run=True
```

## Try Variations

- Add a new argument for timeout or verbosity
- Use [`Actions.APPEND`](pdoc:herogold.argparse.Actions) for list-based arguments
- Combine with validation logic in your main function

## Key Takeaways

The [`Argument`](pdoc:herogold.argparse.Argument) descriptor provides type-safe, declarative CLI argument definitions that integrate seamlessly with argparse.
