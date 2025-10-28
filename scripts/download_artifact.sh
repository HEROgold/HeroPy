#!/usr/bin/env bash
set -euo pipefail
# Usage: download_artifact.sh <workflow-file> <artifact-name> <target-dir>
workflow_file=${1:?}
artifact_name=${2:?}
target_dir=${3:-artifacts}
repo=${GITHUB_REPOSITORY:-${GITHUB_REPOSITORY}}
if [ -z "$GITHUB_TOKEN" ]; then
  echo "GITHUB_TOKEN is required to download workflow artifacts" >&2
  exit 2
fi
echo "Looking for latest successful run for $workflow_file"
run_id=$(gh api "repos/${GITHUB_REPOSITORY}/actions/workflows/${workflow_file}/runs?per_page=20&status=success" -q '.workflow_runs[0].id')
if [ -z "$run_id" ] || [ "$run_id" = "null" ]; then
  echo "no previous run found for $workflow_file" >&2
  exit 1
fi
mkdir -p "$target_dir"
gh run download "$run_id" --name "$artifact_name" --dir "$target_dir"
echo "Downloaded artifacts into $target_dir"
