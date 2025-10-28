#!/usr/bin/env python3
"""Compute version diffs for root and subpackages versus origin/main and write results to GITHUB_OUTPUT.

This script is designed for GitHub Actions. It writes many outputs like
root_changed, root_version, backup_changed, backup_version, etc. to GITHUB_OUTPUT.
"""
import tomllib
import subprocess
import os
from pathlib import Path

def read_at(ref, path):
    try:
        out = subprocess.check_output(['git','show', f'{ref}:{path}'])
        return out.decode()
    except subprocess.CalledProcessError:
        return ''

def version_from_text(txt: str) -> str:
    if not txt or not txt.strip():
        return ''
    data = tomllib.loads(txt)
    return data.get('project', {}).get('version') or data.get('tool', {}).get('poetry', {}).get('version') or ''

def write_output(k, v):
    gho = os.environ.get('GITHUB_OUTPUT')
    line = f"{k}={v}\n"
    if gho:
        with open(gho, 'a') as f:
            f.write(line)
    else:
        print(line, end='')

def main():
    repo_root = Path('.')
    prev_ref = 'origin-main'
    # root
    cur_root_txt = (repo_root / 'pyproject.toml').read_text() if (repo_root / 'pyproject.toml').exists() else ''
    prev_root_txt = read_at(prev_ref, 'pyproject.toml')
    cur_root_v = version_from_text(cur_root_txt)
    prev_root_v = version_from_text(prev_root_txt)

    pkgs = ['backup','color','config','examples','log','rainbow','sentinel','tree']
    results = {
        'root_changed': 'true' if cur_root_v and cur_root_v != prev_root_v else 'false',
        'root_version': cur_root_v,
    }

    for p in pkgs:
        cur_txt = read_at('HEAD', f'herogold/{p}/pyproject.toml') or ''
        prev_txt = read_at(prev_ref, f'herogold/{p}/pyproject.toml') or ''
        cv = version_from_text(cur_txt)
        pv = version_from_text(prev_txt)
        results[f'{p}_changed'] = 'true' if cv and cv != pv else 'false'
        results[f'{p}_version'] = cv

    # write a single JSON output called 'diffs'
    import json
    diffs_json = json.dumps(results, ensure_ascii=False)
    write_output('diffs', diffs_json)

if __name__ == '__main__':
    main()
