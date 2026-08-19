#!/bin/bash
# Convert a Codex session (jsonl) to Markdown. Accepts an exact session_id,
# or a regex matched against titles (which must match exactly one session).
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <session_id>|<title_regex>"
    echo "example: $BASENAME 01a01782-e9e4-7973-a588-b76662e8e961"
    echo "example: $BASENAME 'session.*markdown'"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Expected exactly one argument"
  exit 1
fi

exec python3 "$SCRIPT_DIR/codex_session_to_markdown.py" "$1"
