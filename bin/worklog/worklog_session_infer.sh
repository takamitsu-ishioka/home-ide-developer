#!/usr/bin/env bash
# worklog_session_turns_list.shが出すturn単位のJSON(stdin)を、(repo,ticket)が連続する
# 区間ごとに集約し、ticket別の作業時間候補をJSON配列でstdoutへ出力する(読み取り専用)。
# freeeの打刻は外枠として使わない(その日の最初のturn〜最後のturnがそのまま外枠になる。
# design.md参照: 打刻を「作業時間の外枠」として扱わない方針への転換)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 0 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT < turns.json" >&2
  echo "  stdin: worklog_session_turns_list.shが出すJSON配列" >&2
  echo "example: worklog_session_turns_list.sh 2026-08-24 none | $SCRIPT" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/worklog_session_infer.py"
