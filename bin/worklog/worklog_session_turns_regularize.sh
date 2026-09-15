#!/usr/bin/env bash
# 交換形式のturns JSON(stdin)を受け取り、正規化(regularize)して標準出力する(読み取り専用フィルタ)。
# 1. cwd解決できなかったturn(ticket==GENERAL-451)を、実チケットではないと分かる特殊ticket
#    "_nondeterministic_"へ書き換える
# 2. turn NとN+1の間に実際の空白(gap)があれば、その境界にticket="_gap_"のturnを挿入する
#    (gapサイズは「N+1自身の処理開始時刻 - Nの完了時刻」。N自身の処理時間・N+1自身の処理時間は
#    gapに含めない)
# どちらの特殊ticketも、実ticketへの変換はworklog_session_turns_guess_ticket.shのルールの
# 責務であり、本スクリプトはそれ以上の推論を行わない。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 0 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT < turns.json" >&2
  echo "example: worklog_session_turns_list.sh 2026-08-27 none | $SCRIPT" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/worklog_session_turns_regularize.py" "$@"
