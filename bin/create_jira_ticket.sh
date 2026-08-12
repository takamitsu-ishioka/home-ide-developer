#!/usr/bin/env bash
# Create a Jira ticket from a JSONC ticket definition piped via stdin.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -t 0 ]; then
    echo "$(basename "$0"): input is required" >&2
    echo "usage: $(basename "$0")" >&2
    echo "example: $(basename "$0") < ticket.jsonc" >&2
    exit 1
fi
python3 "$SCRIPT_DIR/create_jira_ticket.py"
