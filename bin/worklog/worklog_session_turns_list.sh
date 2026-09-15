#!/usr/bin/env bash
# 指定日のClaude Codeセッションログから「ターン」(1プロンプト:1レスポンス)を時刻順に
# 抽出し、各ターンのuser(人間が実際に打った発言)・agent(トップレベルagentのユーザー
# 向け発言。サブエージェント呼び出しは"calling subagent for ..."/"回答が来ました。..."と
# いう事実のみを記録し、対話内容そのものは含めない)をJSONでstdoutへ出力する(読み取り専用)。
# 各行のテキストはlimit文字を超えると"...(他N文字)"に切り詰められる。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 2 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <date> <limit>" >&2
  echo "  date : YYYY-MM-DD" >&2
  echo "  limit: 各行の文字数上限(0以上の整数)、または none(切り詰めない)" >&2
  echo "example: $SCRIPT 2026-08-24 200" >&2
  echo "example: $SCRIPT 2026-08-24 none" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/worklog_session_turns_list.py" "$@"
