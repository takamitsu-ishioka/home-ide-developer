#!/bin/bash
# Run one non-interactive Claude prompt and print only its token usage.
# The prompt is read from stdin; Claude's response text is discarded.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <json|tsv>"
    echo "example: printf '%s\\n' 'Review this design.' | $BASENAME json"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Expected exactly one output-format argument"
  exit 1
fi

case "$1" in
  json|tsv)
    OUTPUT_FORMAT="$1"
    ;;
  *)
    usage "Unknown format '$1', expected json or tsv"
    exit 1
    ;;
esac

if [ -t 0 ]; then
  usage "Prompt input is required on stdin"
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "$BASENAME: claude command not found" >&2
  echo "$BASENAME: Install Claude Code and retry" >&2
  exit 1
fi

timestamp() {
  TZ=Asia/Tokyo date '+%Y-%m-%dT%H:%M:%S%z'
}

echo "$(timestamp) Starting Claude without tools or session persistence" >&2

claude -p \
  --output-format json \
  --no-session-persistence \
  --permission-mode dontAsk \
  --tools "" \
  | python3 "$SCRIPT_DIR/claude_usage_report.py" "$OUTPUT_FORMAT"

echo "$(timestamp) Claude token usage reported; response text discarded" >&2
