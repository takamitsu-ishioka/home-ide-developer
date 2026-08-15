#!/bin/bash
# Claude Code statusLine: display the "current repository" (persisted at
# ~/current_repo, see current_repo_set.sh).
set -euo pipefail

cat >/dev/null  # statusLine's stdin JSON isn't needed here; drain it.

if [ -s "$HOME/current_repo" ]; then
  python3 -c "import json; print('repo: ' + json.load(open('$HOME/current_repo')).get('name', '?'))"
else
  echo "repo: (none)"
fi
