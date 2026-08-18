#!/bin/bash
# Report cost/duration/token/code-change stats for one Claude Code session as
# JSON, computed locally from its transcript (~/.claude/projects/**/<id>.jsonl).
# Run with no arguments to list sessions (sorted by last update).
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <session_id>"
    echo "example: $BASENAME 501c69e7-ffc3-497d-87f2-1ccd397242ab"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -eq 0 ]; then
  usage "Missing session_id"
  python3 "$SCRIPT_DIR/claude_session_usage_report.py" --list
  exit $?
fi

if [ "$#" -ne 1 ] || [[ "$1" == -* ]]; then
  usage "Wrong number of arguments"
  exit 1
fi

exec python3 "$SCRIPT_DIR/claude_session_usage_report.py" "$1"
