#!/usr/bin/env bash
# Google Calendarの既存の予定から、通知(ポップアップ)を1件削除する(副作用あり)。
# 指定した値と一致する通知だけを取り除く(他の通知は保持したまま)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

flag_args=()
args=()
for a in "$@"; do
  if [ "$a" = "--dry-run" ] || [ "$a" = "--confirm" ]; then
    flag_args+=("$a")
  else
    args+=("$a")
  fi
done

if [ "${#args[@]}" -ne 2 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <event_id> <reminder> [--dry-run] [--confirm]" >&2
  echo "  event_id: gcal_event_add.shが登録時に出力するid" >&2
  echo "  reminder: 削除したい通知の設定値(HH:MM。例: 6時間前なら06:00)" >&2
  echo "example: $SCRIPT jsi2rum5ph3kc5shmcrren57vc 06:00 --confirm" >&2
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

exec python3 "$SCRIPT_DIR/gcal_event_reminder_delete.py" "${args[@]}" "${flag_args[@]}"
