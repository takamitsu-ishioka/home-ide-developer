#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -t 0 ]; then
    echo "$(basename "$0"): input is required" >&2
    echo "usage: $(basename "$0") [--dry-run]" >&2
    echo "example: $(basename "$0") < page.jsonc" >&2
    exit 1
fi
python3 "$SCRIPT_DIR/conflu_create_page.py" "$@"
