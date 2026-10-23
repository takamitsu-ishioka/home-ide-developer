#!/usr/bin/env bash
# Find today's (local date) Claude Code session for a given directory.
# See claude_session_today_find.py for the matching logic.
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

valid_args=1
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  valid_args=0
elif [ "$#" -eq 2 ] && [ "$2" != "tsv" ] && [ "$2" != "json" ]; then
  valid_args=0
fi

if [ "$valid_args" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <dir> [tsv|json]" >&2
  echo "  tsv|json: 指定するとフルレコード(title/session_id/path/ctime/mtime/message_count/cwd)を出力する。省略時はsession_idのみを出力する(従来動作)" >&2
  echo "example: $SCRIPT \$(pwd)" >&2
  echo "example: $SCRIPT \$(pwd) json" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/claude_session_today_find.py" "$@"
