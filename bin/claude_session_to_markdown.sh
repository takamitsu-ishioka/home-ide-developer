#!/bin/bash
# Convert a Claude Code session (jsonl) to Markdown; run with no args to list sessions.
basename=$(basename "$0")

if [ $# -eq 0 ]; then
    echo "$basename: Too few arguments" >&2
    echo "usage: $basename <session_id_or_jsonl_path>" >&2
    echo "example: $basename 501c69e7-ffc3-497d-87f2-1ccd397242ab" >&2
    python3 "$(dirname "$0")/claude_session_to_markdown.py" --list
    exit $?
fi

if [ $# -ne 1 ]; then
    echo "$basename: Too many arguments" >&2
    echo "usage: $basename [<session_id_or_jsonl_path>]" >&2
    echo "       $basename                               # セッション一覧を表示" >&2
    echo "       $basename 501c69e7-ffc3-497d-87f2-1ccd397242ab" >&2
    exit 1
fi

input="$1"

if [ -f "$input" ]; then
    jsonl_path="$input"
else
    jsonl_path=$(find ~/.claude/projects -name "${input}.jsonl" 2>/dev/null | head -1)
    if [ -z "$jsonl_path" ]; then
        echo "$basename: Session not found: $input" >&2
        exit 1
    fi
fi

python3 "$(dirname "$0")/claude_session_to_markdown.py" "$jsonl_path"
