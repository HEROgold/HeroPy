#!/usr/bin/env python3
r"""Read version from a pyproject.toml and optionally write to GITHUB_OUTPUT.

Usage: get_version.py path/to/pyproject.toml [--output-name NAME]
If GITHUB_OUTPUT is present in the environment, the script will append
"{NAME}={version}\n" to that file so the calling step can capture outputs.
"""
import argparse
import os
from pathlib import Path

import tomllib


def version_from_text(txt: str) -> str:
    if not txt.strip():
        return ""
    data = tomllib.loads(txt)
    return data.get("project", {}).get("version") or data.get("tool", {}).get("poetry", {}).get("version") or ""

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--output-name", default="version")
    args = p.parse_args()
    fp = Path(args.path)
    if not fp.exists():
        version = ""
    else:
        txt = fp.read_text()
        version = version_from_text(txt)

    out_name = args.output_name
    # write to GITHUB_OUTPUT if available
    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho, "a") as f:
            f.write(f"{out_name}={version}\n")
    else:
        pass

if __name__ == "__main__":
    main()
