#!/bin/bash
# Convert a Claude Code or Codex session to Markdown, or list its sessions.
# Give only the agent name to list sessions; add a session ID to convert one.
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    {
        echo "$BASENAME: $1"
        echo "usage: $BASENAME <claude|codex> [<session_id>]"
        echo "example: $BASENAME codex"
        echo "example: $BASENAME codex 01a00e8e-f546-75c0-b3bc-b737be00ed45"
        echo
        awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
    } >&2
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    usage "Expected an agent name and optional session ID"
    exit 1
fi

case "$1" in
    claude|codex)
        AGENT_NAME="$1"
        ;;
    *)
        usage "Unknown agent '$1', expected claude or codex"
        exit 1
        ;;
esac

if [ "$#" -eq 1 ]; then
    exec python3 "$SCRIPT_DIR/agent_session_to_markdown.py" "$AGENT_NAME" --list
fi

if [[ "$2" == -* ]]; then
    usage "Invalid session ID '$2'"
    exit 1
fi

exec python3 "$SCRIPT_DIR/agent_session_to_markdown.py" "$AGENT_NAME" "$2"
