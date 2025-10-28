#!/usr/bin/env python3
"""Compare pyproject version between HEAD and a previous git ref and set GITHUB_OUTPUT changed=true/false and version="".

Usage: compare_version.py path/to/pyproject.toml [previous-ref]
If previous-ref is omitted the script will try to read GITHUB_EVENT_BEFORE env var.
Writes 'changed' and 'version' to GITHUB_OUTPUT when available.
"""
import os
import subprocess
import sys
from pathlib import Path

import tomllib


def version_from_text(txt: str) -> str:
    if not txt.strip():
        return ""
    data = tomllib.loads(txt)
    return data.get("project", {}).get("version") or data.get("tool", {}).get("poetry", {}).get("version") or ""

def read_at(ref: str, path: str) -> str:
    try:
        out = subprocess.check_output(["git","show", f"{ref}:{path}"])
        return out.decode()
    except subprocess.CalledProcessError:
        return ""

def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(2)
    path = sys.argv[1]
    prev_ref = sys.argv[2] if len(sys.argv) >=3 else os.environ.get("GITHUB_EVENT_BEFORE","")

    cur_txt = Path(path).read_text() if Path(path).exists() else ""
    prev_txt = read_at(prev_ref, path) if prev_ref else ""
    cv = version_from_text(cur_txt)
    pv = version_from_text(prev_txt)
    changed = "true" if cv and cv != pv else "false"

    gho = os.environ.get("GITHUB_OUTPUT")
    if gho:
        with open(gho,"a") as f:
            f.write(f"changed={changed}\n")
            f.write(f"version={cv}\n")
    else:
        pass

if __name__ == "__main__":
    main()
