#!/bin/bash
# Report duration and token stats for one Codex session as JSON, computed
# locally from ~/.codex/sessions/**/*.jsonl. With no arguments, list sessions.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <session_id>"
    echo "example: $BASENAME 01a01782-e9e4-7973-a588-b76662e8e961"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -eq 0 ]; then
  usage "Missing session_id"
  python3 "$SCRIPT_DIR/codex_session_usage_report.py" --list
  exit $?
fi
if [ "$#" -ne 1 ] || [[ "$1" == -* ]]; then
  usage "Wrong number of arguments"
  exit 1
fi
exec python3 "$SCRIPT_DIR/codex_session_usage_report.py" "$1"
