#!/bin/bash
# List Claude Code sessions (session_id, title, message_count, mtime, path),
# excluding subagents/ (forked-agent transcripts, not top-level sessions),
# newest first.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <tsv|json>"
    echo "example: $BASENAME tsv | column -t -s \$'\\t'"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ] || { [ "$1" != "tsv" ] && [ "$1" != "json" ]; }; then
  usage "Expected exactly one output-format argument"
  exit 1
fi

exec python3 "$SCRIPT_DIR/claude_session_list.py" "$1"
