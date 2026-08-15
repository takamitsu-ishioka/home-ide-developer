#!/bin/bash
# Claude Code statusLine: display the "current repository" (persisted at
# <repo_local_dir.sh>/current_repo, see current_repo_set.sh).
set -euo pipefail

cat >/dev/null  # statusLine's stdin JSON isn't needed here; drain it.

repo_file="$(repo_local_dir.sh 2>/dev/null || true)/current_repo"

if [ -s "$repo_file" ]; then
  python3 -c "import json; print('repo: ' + json.load(open('$repo_file')).get('name', '?'))"
else
  echo "repo: (none)"
fi
