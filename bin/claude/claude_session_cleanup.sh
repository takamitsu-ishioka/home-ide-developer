#!/bin/bash
# Delete throwaway Claude Code sessions: no title (neither ai-title nor a
# manual /rename) and at most one exchange. Always prints the candidate
# list to stderr first. With neither flag, deletes immediately (for
# scripted/cron use); --dry-run only ever prints the plan; --confirm asks
# once before deleting. --dry-run wins if both are given.
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
  case "$arg" in
    --dry-run|--confirm) ;;
    *)
      usage "Unknown option: $arg"
      exit 1
      ;;
  esac
done

if [ "$#" -gt 2 ]; then
  usage "Too many arguments"
  exit 1
fi

exec python3 "$SCRIPT_DIR/claude_session_cleanup.py" "$@"
