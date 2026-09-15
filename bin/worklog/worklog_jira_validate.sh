#!/usr/bin/env bash
# 指定期間について、bin/worklog/log/<date>.json群とJira worklog(自分の分)の整合性を
# 検査する(読み取り専用)。date+ticket単位で、local_state(投稿済み/未投稿/混在/なし)と
# match(一致/不一致/比較不能)の2列に分解して表(人間向け、厳密なTSVではない)で報告する。
# ticketレベルの記録が一件も無いdateはfreeeの勤怠区分(勤務/休日/休暇/未投稿)で分類する。
# 問題あり(要確認)であれば非0終了。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 2 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <from_date> <to_date>" >&2
  echo "  from_date, to_date: YYYY-MM-DD(両端を含む)" >&2
  echo "example: $SCRIPT 2026-08-17 2026-08-23" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

ENV_FILE="${WORKLOG_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 "$SCRIPT_DIR/worklog_jira_validate.py" "$@"
