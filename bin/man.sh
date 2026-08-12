#!/bin/bash
# List commands in ~/bin with descriptions, or navigate subdirectories.
# Tree-format display with configurable depth and width.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/man.py" "$@"
