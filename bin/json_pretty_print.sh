#!/bin/bash
# Pretty-print a one-line (or otherwise compact) JSON file or stdin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"

if [ $# -gt 1 ] || ([ $# -eq 1 ] && [[ "$1" == -* ]]); then
    echo "${SCRIPT_NAME}: Invalid arguments" >&2
    echo "usage: ${SCRIPT_NAME} [file]" >&2
    echo "example: ${SCRIPT_NAME} data.json" >&2
    echo "example: cat data.json | ${SCRIPT_NAME}" >&2
    exit 1
fi

python3 "${SCRIPT_DIR}/json_pretty_print.py" "$@"
