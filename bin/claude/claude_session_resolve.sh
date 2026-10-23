#!/bin/bash
# Resolve an exact session_id, or a regex matched against session titles, to
# a single session_id (printed to stdout). Fails if zero or more than one
# session matches. See claude_session_list.sh to see titles/narrow it down.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <session_id>|<title_regex>"
    echo "example: $BASENAME 501c69e7-ffc3-497d-87f2-1ccd397242ab"
    echo "example: $BASENAME 'carecom'"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Expected exactly one argument"
  exit 1
fi

exec python3 "$SCRIPT_DIR/claude_session_resolve.py" "$1"
