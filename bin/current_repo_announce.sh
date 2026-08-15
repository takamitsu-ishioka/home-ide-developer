#!/bin/bash
# Claude Code SessionStart hook: if a "current repository" was persisted
# in a previous session (see current_repo_set.sh,
# <repo_local_dir.sh>/current_repo), inject it as context so the model
# knows about it from the start of this new session too, without the user
# having to re-select it. Runs after repo_name_sync.sh in the SessionStart
# hook list, so the local-root directory is already correctly named by
# the time this resolves it.
set -euo pipefail

cat >/dev/null  # SessionStart's stdin JSON isn't needed here; drain it.

repo_file="$(repo_local_dir.sh 2>/dev/null || true)/current_repo"

if [ -s "$repo_file" ]; then
  python3 -c "
import json
repo = json.load(open('$repo_file'))
context = (
    'Current repository (persisted from a previous session): '
    + repo.get('name', '?') + ' at ' + repo.get('path', '?')
    + ' (branch: ' + repo.get('branch', '?') + ')'
)
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': context}}))
"
fi
