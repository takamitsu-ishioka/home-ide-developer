#!/usr/bin/env bash
# 自分にアサインされ、statusCategoryがDoneでない(backlog/進行中)Jiraチケットを一覧する
# (読み取り専用)。key, status, summary, urlをtsvまたはjson形式で標準出力へ返す。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 1 ] || { [ "$1" != "tsv" ] && [ "$1" != "json" ]; }; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <tsv|json>" >&2
  echo "example: $SCRIPT tsv" >&2
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

exec python3 "$SCRIPT_DIR/worklog_jira_ticket_list.py" "$@"
