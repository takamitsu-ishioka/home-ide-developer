#!/bin/bash
# Convert a Claude Code session (jsonl) to Markdown; run with no args to list sessions.
basename=$(basename "$0")

if [ $# -eq 0 ]; then
    echo "$basename: Too few arguments" >&2
    echo "usage: $basename <session_id>" >&2
    echo "example: $basename 501c69e7-ffc3-497d-87f2-1ccd397242ab" >&2
    python3 "$(dirname "$0")/claude_session_to_markdown.py" --list
    exit $?
fi

if [ $# -ne 1 ] || [[ "$1" == -* ]]; then
    echo "$basename: Invalid arguments" >&2
    echo "usage: $basename [<session_id>]" >&2
    echo "       $basename                               # list sessions (sorted by last update)" >&2
    echo "       $basename 501c69e7-ffc3-497d-87f2-1ccd397242ab" >&2
    exit 1
fi

session_id="$1"

jsonl_path=$(find ~/.claude/projects -name "${session_id}.jsonl" 2>/dev/null | head -1)
if [ -z "$jsonl_path" ]; then
    echo "$basename: Session not found: $session_id" >&2
    exit 1
fi

python3 "$(dirname "$0")/claude_session_to_markdown.py" "$jsonl_path"
