#!/bin/bash
# Delete throwaway Codex sessions: no title and at most one user message.
# Always prints candidates first. Default deletes immediately; --dry-run only
# prints the plan; --confirm asks once. --dry-run wins when both are supplied.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME [--dry-run] [--confirm]"
    echo "example: $BASENAME --dry-run"
    echo "example: $BASENAME --confirm"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

for arg in "$@"; do
  case "$arg" in --dry-run|--confirm) ;; *) usage "Unknown option: $arg"; exit 1;; esac
done
if [ "$#" -gt 2 ]; then usage "Too many arguments"; exit 1; fi
exec python3 "$SCRIPT_DIR/codex_session_cleanup.py" "$@"
