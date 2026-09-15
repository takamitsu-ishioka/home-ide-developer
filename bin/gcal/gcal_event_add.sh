#!/usr/bin/env bash
# Google Calendarへ予定を1件作成する(副作用あり)。日時はローカルタイム(Asia/Tokyo)。
# 初回利用にはget_credentials.shでの認可が必要(README.md参照)。
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

if [ "${#args[@]}" -ne 6 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <date> <start_hm> <end_hm> <reminder> <title> <description> [--dry-run] [--confirm]" >&2
  echo "  date: TODAY, TOMORROW, または YYYY-MM-DD" >&2
  echo "  start_hm, end_hm: HH:MM(ローカルタイム, Asia/Tokyo)" >&2
  echo "  reminder: 予定の何時間何分前に通知するか(HH:MM。例: 6時間前なら06:00) または none(通知なし)" >&2
  echo "  title: 予定のタイトル(1つの引数として渡す。空白を含む場合はクォートすること)" >&2
  echo "  description: 予定の説明(1つの引数として渡す) または none(説明なし)" >&2
  echo "example: $SCRIPT TOMORROW 08:00 08:30 00:00 \"DADC 03-5978-7541\" none --confirm" >&2
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

exec python3 "$SCRIPT_DIR/gcal_event_add.py" "${args[@]}" "${flag_args[@]}"
