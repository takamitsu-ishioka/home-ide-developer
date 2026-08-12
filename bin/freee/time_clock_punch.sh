#!/usr/bin/env bash
# freee人事労務APIで打刻を1件登録する(出勤・休憩開始・休憩終了・退勤)
# 当日以外の日付を指定した場合はdatetimeを明示送信する(freee仕様上、管理者権限が必要)
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

valid_args=1
if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
  valid_args=0
else
  for extra_arg in "${@:3}"; do
    case "$extra_arg" in
      --dry-run|--confirm) ;;
      *) valid_args=0 ;;
    esac
  done
  if [ "$#" -eq 4 ] && [ "${3}" = "${4}" ]; then
    valid_args=0
  fi
fi

if [ "$valid_args" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <type> <date> [--dry-run] [--confirm]" >&2
  echo "  type: clock_in(出勤) | break_begin(休憩開始) | break_end(休憩終了) | clock_out(退勤)" >&2
  echo "  date: TODAY(当日) または対象年月日(YYYY-MM-DD)。当日以外を指定するとdatetimeを明示送信する(管理者権限が必要)" >&2
  echo "  --dry-run と --confirm は独立したオプション(併用可、順不同):" >&2
  echo "    --dry-run: 実際には打刻登録を行わず、登録可否のみ確認する" >&2
  echo "    --confirm: 実行前に(Y/n)で確認を求める(--dry-runの有無に関わらず)。指定しない場合、確認なしで即座に進む" >&2
  echo "example: $SCRIPT clock_in TODAY" >&2
  echo "example: $SCRIPT clock_in TODAY --dry-run" >&2
  echo "example: $SCRIPT clock_out 2026-08-04 --confirm" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

ENV_FILE="${FREEE_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 "$SCRIPT_DIR/time_clock_punch.py" "$@"
