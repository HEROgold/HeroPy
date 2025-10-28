# Fetch Subpackage Artifact Action

This composite action downloads and unpacks a subpackage artifact from a previous workflow run.

## Purpose

This action is used in the root release workflow (`release-root.yml`) to fetch pre-built artifacts for subpackages that haven't changed, avoiding unnecessary rebuilds.

## Inputs

### `subpackage` (required)
Name of the subpackage (e.g., `backup`, `sentinel`, `color`, etc.)

### `version` (required)
Version of the subpackage artifact to fetch

### `github-token` (optional)
GitHub token for artifact operations. Defaults to `${{ github.token }}`.

## Usage Example

```yaml
- name: Checkout
  uses: actions/checkout@v5

- name: Fetch backup artifact
  uses: ./.github/actions/fetch-subpackage-artifact
  with:
    subpackage: backup
    version: 1.0.0
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

## How It Works

1. Uses the `download_artifact.sh` script to fetch the artifact by workflow name and artifact name
2. Uses the `unpack_artifacts.sh` script to extract the artifact to `dist/<subpackage>/`

This action consolidates the repetitive artifact fetching logic that was previously duplicated across multiple jobs in the release workflow.
