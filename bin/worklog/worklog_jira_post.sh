#!/usr/bin/env bash
# JiraネイティブのworklogエンドポイントにJira APIトークンで1件作業時間を登録する。
# ダッシュボード10011(Tempo Timesheet)にJiraネイティブworklogが反映されるかどうかを
# 実測で確認するための検証スクリプト(design.md #4 / 未決事項参照)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

valid_args=1
if [ "$#" -lt 4 ] || [ "$#" -gt 6 ]; then
  valid_args=0
else
  for extra_arg in "${@:5}"; do
    case "$extra_arg" in
      --dry-run|--confirm) ;;
      *) valid_args=0 ;;
    esac
  done
  if [ "$#" -eq 6 ] && [ "${5}" = "${6}" ]; then
    valid_args=0
  fi
fi

if [ "$valid_args" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <issue_key> <started> <time_spent_seconds> <comment> [--dry-run] [--confirm]" >&2
  echo "  issue_key         : 対象issue key (例: MMWAVE-787)" >&2
  echo "  started           : 作業開始時刻。NOW(現在時刻) または YYYY-MM-DDTHH:MM(ローカルタイム)" >&2
  echo "  time_spent_seconds: 作業時間(秒)" >&2
  echo "  comment           : worklogコメント" >&2
  echo "  --dry-run と --confirm は独立したオプション(併用可、順不同):" >&2
  echo "    --dry-run: 実際には登録を行わず、送信内容のみ表示する" >&2
  echo "    --confirm: 実行前に(Y/n)で確認を求める(--dry-runの有無に関わらず)。指定しない場合、確認なしで即座に進む" >&2
  echo "example: $SCRIPT MMWAVE-787 NOW 60 'ダッシュボード10011反映確認テスト' --dry-run" >&2
  echo "example: $SCRIPT MMWAVE-787 2026-08-20T10:00 3600 '週次会議' --confirm" >&2
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

exec python3 "$SCRIPT_DIR/worklog_jira_post.py" "$@"
