#!/bin/bash
basename=$(basename "$0")
py_script=$(dirname "$0")/sensor_modules.py

dry_run=""

# --dry-run フラグを検出
if [ "$1" = "--dry-run" ]; then
    dry_run="--dry-run"
    shift
fi

if [ $# -lt 3 ]; then
    echo "$basename: Too few arguments" >&2
    echo "usage: $basename [--dry-run] <env_name> <module_type> <version> [sensor_id] [chip_type]" >&2
    echo "example: cat sensor.zip | $basename LOCAL sensor 01030505" >&2
    echo "example: cat sensor.zip | $basename --dry-run LOCAL sensor 01030505" >&2
    echo "" >&2
    echo "API: POST /api/v1/login (AUTH_BASE) — ユーザー認証" >&2
    echo "     POST /api/v1/modules (API_BASE) — モジュール登録（multipart/form-data で 'info' JSON と 'binary' ZIP を送信）" >&2
    exit 1
fi

# --dry-run がある場合とない場合を分ける
if [ -n "$dry_run" ]; then
    python3 "$py_script" put "$dry_run" "$1" "$2" "$3" "$4" "$5"
else
    python3 "$py_script" put "$1" "$2" "$3" "$4" "$5"
fi
