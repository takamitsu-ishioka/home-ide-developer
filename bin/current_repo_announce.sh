#!/bin/bash
# Claude Code SessionStart hook: if a "current repository" was persisted
# in a previous session (see current_repo_set.sh, ~/current_repo), inject
# it as context so the model knows about it from the start of this new
# session too, without the user having to re-select it.
set -euo pipefail

cat >/dev/null  # SessionStart's stdin JSON isn't needed here; drain it.

if [ -s "$HOME/current_repo" ]; then
  python3 -c "
import json
repo = json.load(open('$HOME/current_repo'))
context = (
    'Current repository (persisted from a previous session): '
    + repo.get('name', '?') + ' at ' + repo.get('path', '?')
    + ' (branch: ' + repo.get('branch', '?') + ')'
)
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': context}}))
"
fi
