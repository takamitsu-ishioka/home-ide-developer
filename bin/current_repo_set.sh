#!/bin/bash
# Set the "current repository": persists across Claude Code sessions (not
# session-scoped -- read back at the start of every future session via a
# SessionStart hook, see current_repo_announce.sh) at ~/current_repo (not
# tracked in git -- machine-local, same convention as ~/environment_name).
# Input: one JSON object (path, name, branch, remote_url) on stdin, e.g.
# one element of `git_local_repos_list.sh . json`'s output array.
set -euo pipefail

BASENAME="$(basename "$0")"

if [ -t 0 ]; then
  echo "$BASENAME: input is required" >&2
  echo "usage: $BASENAME < repo.json" >&2
  echo "example: echo '{\"path\":\"/home/developer/ghost\",\"name\":\"ghost\"}' | $BASENAME" >&2
  exit 1
fi

tmp_in="$(mktemp)"
trap 'rm -f "$tmp_in"' EXIT
cat > "$tmp_in"

if ! python3 -c "import json; json.load(open('$tmp_in'))" 2>/dev/null; then
  echo "$BASENAME: input is not valid JSON" >&2
  exit 1
fi

cp "$tmp_in" "$HOME/current_repo"
echo "$BASENAME: current repository updated" >&2
