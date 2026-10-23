#!/usr/bin/env bash
# 交換形式JSON(stdin、レコードの配列)を due_watch の _cache.json へ差分マージする。
# key=(source,id)でupsert。入力に含まれるsourceで入力に無いレコードは除去、期限切れも除去。
# 入力に含まれないsourceのレコードは温存する。
# fetchスクリプト群の出力を連結して渡す想定:
#   ( due_watch_fetch_teams.sh; due_watch_fetch_gmail.sh ) | jq -s add ... ではなく
#   due_watch_poll.sh がまとめて1配列にして渡す。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 0 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT < exchange.json" >&2
  echo "example: due_watch_fetch_teams.sh | $SCRIPT" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/due_watch_cache_update.py"
