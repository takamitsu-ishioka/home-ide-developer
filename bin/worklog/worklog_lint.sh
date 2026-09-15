#!/usr/bin/env bash
# worklog_session_infer.shが出すセグメントJSON(stdin)の妥当性を検査する(読み取り専用)。
# 必須フィールドの有無、date/HH:MM形式、start<end、durationの整合性、同一日内の時間帯
# 重複、date/start昇順、posted_atの形式をチェックする。問題が無ければstdinの内容を
# そのままstdoutへ通す(worklog_tsv_validate.shの後継、JSON版)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 0 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT < segments.json" >&2
  echo "example: worklog_session_turns_list.sh 2026-08-24 none | worklog_session_infer.sh | $SCRIPT" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/worklog_lint.py"
