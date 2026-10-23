#!/usr/bin/env bash
# Find today's (local date) Codex session for a given directory.
# See codex_session_today_find.py for the matching logic.
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <dir>" >&2
  echo "example: $SCRIPT \$(pwd)" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/codex_session_today_find.py" "$@"
