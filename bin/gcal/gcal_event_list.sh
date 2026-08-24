#!/usr/bin/env bash
# Google Calendarの指定日の予定一覧を取得する(読み取り専用)。
# id,date,time,title,reminders(通知設定。予定の何時間何分前かを昇順で並べたもの)を
# jsonまたはtsvでstdoutへ出力する。取り消し済み(cancelled)の予定は除外する。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 2 ] || { [ "$2" != "json" ] && [ "$2" != "tsv" ]; }; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <date> (json|tsv)" >&2
  echo "  date: TODAY, TOMORROW, または YYYY-MM-DD" >&2
  echo "example: $SCRIPT TODAY tsv" >&2
  echo "example: $SCRIPT 2026-08-25 json" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

ENV_FILE="${GCAL_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 "$SCRIPT_DIR/gcal_event_list.py" "$@"
