#!/usr/bin/env bash
set -euo pipefail
# Usage: py_import_checker.sh module_path
module=${1:-}
if [ -z "$module" ]; then
  echo "Usage: $0 <python.module.path>" >&2
  exit 2
fi
python - <<PY
import importlib, sys
mod = "$module"
try:
    importlib.import_module(mod)
    print('import ok')
except Exception as e:
    print('import failed:', e, file=sys.stderr)
    raise
PY
