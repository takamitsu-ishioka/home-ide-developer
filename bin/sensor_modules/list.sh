#!/bin/bash
basename=$(basename "$0")
py_script=$(dirname "$0")/sensor_modules.py

if [ $# -ne 1 ]; then
    echo "$basename: Too few arguments" >&2
    echo "usage: $basename <env_name>" >&2
    echo "example: $basename ALPHA" >&2
    echo "" >&2
    echo "API: POST /api/v1/login (AUTH_BASE) — ユーザー認証" >&2
    echo "     GET /api/v1/modules (API_BASE) — sensor, config, firmware のリストを取得" >&2
    exit 1
fi

python3 "$py_script" list "$1"
