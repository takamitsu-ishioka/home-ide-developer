"""List local git repositories found under a root directory.

Called only from git_local_repos_list.sh (see docs/CLAUDE.md scripting
rules: python is always a thin-wrapped implementation, never run
standalone).

A repo is any directory directly containing a .git entry (directory or
file, so worktrees count too) -- nested repos (e.g. a separately-managed
repo checked out inside another repo's tree) are found too, since a repo
boundary doesn't stop the walk, only .git's own internals do. This is
pure `git`; no GitHub or any other hosting API is involved -- see
~/bin/github/github_repos_list.sh for the GitHub-specific equivalent.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
# Noise, not real personal repos -- pruned so the walk doesn't waste time
# descending into dependency trees and caches.
PRUNE = {'node_modules', '.cache', '__pycache__'}


def log(message: str) -> None:
    timestamp = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S(JST)')
    print(f'{timestamp} {message}', file=sys.stderr)


def git(repo_dir: str, *args: str) -> str:
    result = subprocess.run(
        ['git', '-C', repo_dir, *args], capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ''


def repo_name(repo_dir: str, remote_url: str) -> str:
    # The remote's own name for the repo is preferred -- a checkout
    # directory's basename need not match it (e.g. this repo is cloned at
    # ~/, whose basename is the Linux username "developer").
    if remote_url:
        name = remote_url.rsplit('/', 1)[-1]
        if name.endswith('.git'):
            name = name[:-4]
        return name
    return os.path.basename(repo_dir.rstrip('/'))


def find_repos(root_dir: str):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        has_git = '.git' in dirnames or '.git' in filenames
        if '.git' in dirnames:
            dirnames.remove('.git')
        if has_git:
            yield dirpath


def collect(root_dir: str) -> list[dict]:
    repos = []
    for repo_dir in find_repos(root_dir):
        remote_url = git(repo_dir, 'remote', 'get-url', 'origin')
        repos.append({
            'path': repo_dir,
            'name': repo_name(repo_dir, remote_url),
            'branch': git(repo_dir, 'rev-parse', '--abbrev-ref', 'HEAD'),
            'remote_url': remote_url,
        })
    return repos


def print_tsv(repos: list[dict]) -> None:
    for r in repos:
        print('\t'.join([r['path'], r['name'], r['branch'], r['remote_url']]))


def main() -> None:
    root_dir = sys.argv[1]
    format_ = sys.argv[2]

    log(f'searching for git repositories under {root_dir}...')
    repos = collect(root_dir)

    if format_ == 'tsv':
        print_tsv(repos)
    else:
        print(json.dumps(repos, ensure_ascii=False))

    log(f'done, {len(repos)} repositories.')


if __name__ == '__main__':
    main()
