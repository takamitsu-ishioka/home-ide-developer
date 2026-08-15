#!/bin/bash
# Print the current path of this repo's local-root data directory (the
# one whose own name caches the repo's GitHub name -- see
# ~/.home-ide-developer/README.md). Its name can change (repo_name_sync.sh
# renames it to track the actual repo name), so anything that needs its
# path resolves it dynamically through here rather than hardcoding
# ".home-ide-developer" -- identified by the sentinel file
# .repo-name-marker inside it, not by name.
set -uo pipefail

BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME"
    echo "example: dir=\"\$($BASENAME)\" && cat \"\$dir/current_repo\""
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 0 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

sentinel=".repo-name-marker"
current="$(find "$HOME" -maxdepth 2 -type f -name "$sentinel" 2>/dev/null | head -1)"

if [ -z "$current" ]; then
  echo "$BASENAME: no repo-local data directory found (no $sentinel under \$HOME)" >&2
  exit 1
fi

dirname "$current"
