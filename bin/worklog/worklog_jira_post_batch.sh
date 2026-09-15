#!/usr/bin/env bash
# セグメントJSONファイル(worklog_session_infer.shの出力、人間が確認・編集済みのもの)の
# うち、posted_atが空/無い要素すべてをまとめてJira worklog APIへ登録する。
# 投稿成功した要素にはposted_atを書き込み、同じファイルへ上書き保存する(design.md #10参照)。
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

if [ "${#args[@]}" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <file> [--dry-run] [--confirm]" >&2
  echo "  file: worklog_session_infer.shが出したセグメントJSON(例: bin/worklog/log/2026-08-24.json)" >&2
  echo "  --dry-run と --confirm は独立したオプション(併用可、順不同):" >&2
  echo "    --dry-run: 実際には登録・書き込みを行わず、対象要素と送信内容のみ表示する" >&2
  echo "    --confirm: 実行前に(Y/n)で一括確認を求める(--dry-runの有無に関わらず)。指定しない場合、確認なしで即座に進む" >&2
  echo "example: $SCRIPT bin/worklog/log/2026-08-24.json --dry-run" >&2
  echo "example: $SCRIPT bin/worklog/log/2026-08-24.json --confirm" >&2
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

exec python3 "$SCRIPT_DIR/worklog_jira_post_batch.py" "${args[@]}" "${flag_args[@]}"
