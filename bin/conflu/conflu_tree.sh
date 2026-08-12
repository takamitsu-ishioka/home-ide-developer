#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ $# -ne 1 ]; then
    echo "$(basename "$0"): Too few arguments" >&2
    echo "usage: $(basename "$0") <space_key>" >&2
    echo "example: $(basename "$0") MMWAVE" >&2
    exit 1
fi
python3 "$SCRIPT_DIR/conflu_tree.py" "$1"
