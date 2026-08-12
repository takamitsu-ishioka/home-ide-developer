#!/bin/bash
basename=$(basename "$0")
py_script=$(dirname "$0")/sensor_modules.py

if [ $# -ne 2 ]; then
    echo "$basename: Too few arguments" >&2
    echo "usage: $basename <env_name> <module_id>" >&2
    echo "example: $basename ALPHA sensor_01030505" >&2
    echo "" >&2
    echo "API: POST /api/v1/login (AUTH_BASE) — ユーザー認証" >&2
    echo "     GET /api/v1/modules/{module_id} (SENSOR_BASE) — 指定モジュールのバイナリ取得" >&2
    exit 1
fi

python3 "$py_script" get "$1" "$2"
