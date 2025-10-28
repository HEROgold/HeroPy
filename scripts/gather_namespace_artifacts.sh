#!/usr/bin/env bash
set -euo pipefail
# Collect all package dist contents under dist/<pkg> into a single namespace_dist folder
target=namespace_dist
rm -rf "$target"
mkdir -p "$target"
if [ -d dist ]; then
  for d in dist/*; do
    if [ -d "$d" ]; then
      echo "Copying from $d"
      cp -r "$d"/* "$target/" || true
    fi
  done
fi
echo "Namespace artifacts gathered into $target"
