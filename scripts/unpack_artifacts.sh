#!/usr/bin/env bash
set -euo pipefail
# Usage: unpack_artifacts.sh <artifacts-dir> <target-dist-dir>
artifacts_dir=${1:-artifacts}
target_dir=${2:-dist}
mkdir -p "$target_dir"
if [ -d "$artifacts_dir" ]; then
  for f in "$artifacts_dir"/*; do
    if [ -f "$f" ]; then
      # try unzip, if fails just copy
      if file "$f" | grep -q zip; then
        unzip -o "$f" -d "$target_dir" || true
      else
        cp -v "$f" "$target_dir/" || true
      fi
    fi
  done
fi
echo "Unpacked artifacts from $artifacts_dir to $target_dir"
