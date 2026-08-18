#!/bin/bash
# Report this machine's cached 5-hour/weekly Claude.ai rate-limit usage
# (used_percentage + resets_at), as last seen by any active session's
# statusLine hook. No network calls, no OAuth credentials touched.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME"
    echo "example: $BASENAME"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 0 ]; then
  usage "Expected no arguments"
  exit 1
fi

exec python3 "$SCRIPT_DIR/claude_rate_limit_report.py"
