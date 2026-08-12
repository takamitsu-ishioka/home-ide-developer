#!/bin/bash
# Concatenate multiple JSON-array files into a single JSON array (stdout).
# Unlike `cat`, which just concatenates bytes and produces invalid JSON
# when fed several arrays back to back, this merges their elements into one
# array. Each input file's top-level JSON must be an array.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"

if [ $# -lt 1 ]; then
    echo "${SCRIPT_NAME}: Invalid arguments" >&2
    echo "usage: ${SCRIPT_NAME} <file1.json> [file2.json ...]" >&2
    echo "example: ${SCRIPT_NAME} a.json b.json > merged.json" >&2
    echo "example: ${SCRIPT_NAME} dir/*/*.json | sleep_probability_calculate.sh 0 json" >&2
    exit 1
fi

python3 "${SCRIPT_DIR}/json_array_concat.py" "$@"
