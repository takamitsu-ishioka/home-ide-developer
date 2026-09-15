#!/usr/bin/env bash
# 指定日のJira worklog(自分がJiraへ既に登録した分)をセグメントJSONファイルへ取り込む
# (Jira => 交換形式の同期)。1対1に対応するローカル未投稿要素があればposted_atを埋め、
# 対応する要素が無ければ新規要素として追加する。fileが存在しなければ新規作成する。
# worklog_jira_post_batch.shの逆方向(交換形式 => Jira)と対をなす。
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
  echo "usage: $SCRIPT <date> <file> [--dry-run] [--confirm]" >&2
  echo "  date: YYYY-MM-DD" >&2
  echo "  file: セグメントJSON(例: bin/worklog/log/2026-08-17.json。無ければ新規作成)" >&2
  echo "  --dry-run と --confirm は独立したオプション(併用可、順不同):" >&2
  echo "    --dry-run: 実際には書き込みを行わず、対象内容のみ表示する" >&2
  echo "    --confirm: 実行前に(Y/n)で確認を求める(--dry-runの有無に関わらず)。指定しない場合、確認なしで即座に進む" >&2
  echo "example: $SCRIPT 2026-08-17 bin/worklog/log/2026-08-17.json --dry-run" >&2
  echo "example: $SCRIPT 2026-08-17 bin/worklog/log/2026-08-17.json --confirm" >&2
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

exec python3 "$SCRIPT_DIR/worklog_jira_sync.py" "${args[@]}" "${flag_args[@]}"
