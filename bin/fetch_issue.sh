#!/bin/bash
# Fetch a GitHub issue (title/body/comments) as JSON via gh CLI.

SCRIPT=$(basename "$0")

if [ $# -ne 2 ]; then
    echo "$SCRIPT: Too few arguments" >&2
    echo "usage: $SCRIPT <repository> <issue_number>" >&2
    echo "example: $SCRIPT uenoyama-dominosoft/fl-mmwave 221" >&2
    exit 1
fi

REPOSITORY="$1"
NUMBER="$2"
PROPERTIES="title,body,comments"

gh issue view "$NUMBER" --repo "$REPOSITORY" --json "$PROPERTIES" \
| python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), indent=2, ensure_ascii=False))"
