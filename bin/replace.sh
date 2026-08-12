#!/bin/bash
# Apply a named regex replacement (from replace.regex/) to a file or stdin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"

if [ $# -lt 1 ]; then
    REGEX_DIR="${SCRIPT_DIR}/replace.regex"
    AVAILABLE=$(ls "${REGEX_DIR}"/*.regex 2>/dev/null | xargs -I{} basename {} .regex | tr '\n' ',' | sed 's/,$//')
    echo "${SCRIPT_NAME}: Too few arguments" >&2
    echo "usage: ${SCRIPT_NAME} <names> [file]" >&2
    echo "example: ${SCRIPT_NAME} bold,chatgpt,me note.md" >&2
    echo "example: cat note.md | ${SCRIPT_NAME} bold,me > out.md" >&2
    echo "regex dir: ${REGEX_DIR}/" >&2
    echo "available: ${AVAILABLE}" >&2
    exit 1
fi

python3 "${SCRIPT_DIR}/replace.py" "$@"
