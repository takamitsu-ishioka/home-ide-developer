#!/usr/bin/env bash
# JiraネイティブのworklogエンドポイントからJira APIトークンで1件のworklogを削除する。
# 既存worklogを訂正する(削除して正しい内容で登録し直す)ための補助スクリプト。
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
  echo "usage: $SCRIPT <issue_key> <worklog_id> [--dry-run] [--confirm]" >&2
  echo "  issue_key  : 対象issue key (例: MMWAVE-787)" >&2
  echo "  worklog_id : 削除するworklogのid(worklog_jira_query経由で調べる)" >&2
  echo "  --dry-run と --confirm は独立したオプション(併用可、順不同):" >&2
  echo "    --dry-run: 実際には削除せず、削除対象のみ表示する" >&2
  echo "    --confirm: 実行前に(Y/n)で確認を求める(--dry-runの有無に関わらず)。指定しない場合、確認なしで即座に進む" >&2
  echo "example: $SCRIPT GENERAL-451 10032 --dry-run" >&2
  echo "example: $SCRIPT GENERAL-451 10032 --confirm" >&2
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

exec python3 "$SCRIPT_DIR/worklog_jira_delete.py" "$@"
