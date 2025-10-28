# Conditional Subpackage Workflow Architecture

## Overview

The HeroPy repository uses a namespace package structure with multiple subpackages (backup, color, config, examples, log, rainbow, sentinel, tree). Each subpackage can be built and released independently.

## Problem Statement

The root release workflow (`release-root.yml`) needs to:
1. Build each subpackage IF its version has changed
2. Fetch the previous artifact IF the version has NOT changed
3. Combine all subpackage artifacts to build the namespace package

The challenge is that this pattern was repeated for each subpackage, leading to a verbose and hard-to-maintain workflow file.

## Solution: Custom GitHub Action

We created a custom composite action at `.github/actions/fetch-subpackage-artifact/` that consolidates the artifact fetching logic.

### What the Action Does

The action encapsulates the common pattern of:
1. Downloading an artifact from a previous workflow run
2. Unpacking it to the correct directory

This eliminates the need to duplicate these steps for each subpackage's fetch job.

### Usage in release-root.yml

```yaml
backup-fetch:
  needs: prepare
  if: ${{ fromJson(needs.prepare.outputs.diffs).backup_changed == 'false' }}
  runs-on: ubuntu-latest
  steps:
    - name: Checkout
      uses: actions/checkout@v5

    - name: Fetch backup artifact
      uses: ./.github/actions/fetch-subpackage-artifact
      with:
        subpackage: backup
        version: ${{ fromJson(needs.prepare.outputs.diffs).backup_version }}
        github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Workflow Structure

### 1. Prepare Job

Runs `scripts/compute_diffs.py` which:
- Compares current versions with versions in `origin/main`
- Outputs a JSON object with version info and change status for each subpackage
- Example output:
  ```json
  {
    "backup_changed": "true",
    "backup_version": "1.0.0",
    "sentinel_changed": "false",
    "sentinel_version": "0.5.2",
    ...
  }
  ```

### 2. Subpackage Jobs (Pattern Repeated for Each)

For each subpackage, there are two jobs:

#### Build Job (if version changed)
- Conditional: `if: ${{ fromJson(needs.prepare.outputs.diffs).<pkg>_changed == 'true' }}`
- Calls the subpackage's release workflow: `./.github/workflows/<pkg>/release.yml`

#### Fetch Job (if version unchanged)
- Conditional: `if: ${{ fromJson(needs.prepare.outputs.diffs).<pkg>_changed == 'false' }}`
- Uses the custom `fetch-subpackage-artifact` action
- Downloads the previously built artifact

### 3. Build Namespace Job

- Waits for all subpackage jobs to complete
- Gathers all artifacts
- Builds the root namespace package
- Creates a GitHub release

## Why Not More Consolidation?

### GitHub Actions Limitations

1. **Can't use matrix for calling workflows**: GitHub Actions doesn't support dynamic `uses:` paths in workflow calls, preventing us from using a matrix strategy like:
   ```yaml
   # This doesn't work:
   strategy:
     matrix:
       subpackage: [backup, color, config, ...]
   uses: ./.github/workflows/${{ matrix.subpackage }}/release.yml
   ```

2. **Can't call reusable workflows from composite actions**: Composite actions can only contain steps, not job definitions or workflow calls.

3. **Can't conditionally call workflows from a matrix**: Even if we could use a matrix, we can't conditionally call different workflows based on the version change status.

### What We Could Do (But Don't)

- **JavaScript Action**: We could create a more complex JavaScript action that makes API calls to trigger workflows, but this would:
  - Be more complex to maintain
  - Lose the declarative workflow structure
  - Make debugging harder
  - Require handling authentication and API rate limits

### What We Did Instead

Created a **composite action** that:
- ✅ Consolidates the artifact fetching logic
- ✅ Is easy to understand and maintain
- ✅ Reduces code duplication
- ✅ Can be easily updated if the fetching logic needs to change
- ✅ Provides clear documentation

## Adding a New Subpackage

To add a new subpackage to the release workflow:

1. Create the subpackage directory: `herogold/newpkg/`
2. Add workflow files:
   - `.github/workflows/newpkg/ci.yml`
   - `.github/workflows/newpkg/release.yml`
   - `.github/workflows/newpkg/release-trigger.yml`
3. Update `scripts/compute_diffs.py`:
   - Add `'newpkg'` to the `pkgs` list
4. Add to `release-root.yml`:
   ```yaml
   newpkg:
     needs: prepare
     if: ${{ fromJson(needs.prepare.outputs.diffs).newpkg_changed == 'true' }}
     uses: ./.github/workflows/newpkg/release.yml

   newpkg-fetch:
     needs: prepare
     if: ${{ fromJson(needs.prepare.outputs.diffs).newpkg_changed == 'false' }}
     runs-on: ubuntu-latest
     steps:
       - name: Checkout
         uses: actions/checkout@v5

       - name: Fetch newpkg artifact
         uses: ./.github/actions/fetch-subpackage-artifact
         with:
           subpackage: newpkg
           version: ${{ fromJson(needs.prepare.outputs.diffs).newpkg_version }}
           github-token: ${{ secrets.GITHUB_TOKEN }}
   ```
5. Add `newpkg` and `newpkg-fetch` to the `needs:` list in `build-namespace` job

## Benefits of This Approach

1. **Maintainability**: Common logic is in one place
2. **Consistency**: All subpackages use the same fetching mechanism
3. **Clarity**: The workflow structure clearly shows the conditional build/fetch pattern
4. **Testability**: The action can be tested independently
5. **Extensibility**: Easy to modify the fetching logic for all subpackages at once

## Future Improvements

If GitHub Actions adds support for:
- Dynamic workflow paths in `uses:` fields
- Matrix strategies with reusable workflows
- More powerful conditional logic

We could further consolidate this workflow. Until then, this is the optimal structure within GitHub Actions' constraints.
