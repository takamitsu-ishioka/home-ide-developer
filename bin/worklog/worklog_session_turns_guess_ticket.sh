#!/usr/bin/env bash
# 交換形式のturns JSON(stdin)を受け取り、ルールファイル(JSONL)に従ってticketプロパティを
# 書き換える(読み取り専用フィルタ、rules_file自体は書き換えない)。
# ルール1行 = {"if": <条件>, "ticket": "<書き換え後の値>"}。条件はand/or/not(入れ子可)と
# {"property": "<turnのキー名>", "regex": "<正規表現>"}の組み合わせ。propertyの値が配列
# (user/agent)の場合は要素のいずれかがマッチすれば真。"if"にJSONの真偽値trueを指定すると
# 無条件マッチの通常ルールになる(ファイル末尾に置けば最低優先度の既定値として使える)。
# ルールはファイル先頭から順に評価し、先勝ち(最初にマッチしたルールのticketで確定し、
# 以降のルールは評価しない)。マッチするルールが無ければticketは変更しない。
# このスクリプトはturnの既存プロパティだけを見てルールを当てはめる以外の推論を
# 一切行わない(休憩の特別扱い・継続・フォールバック階層のような状態は持たない)。
# 特殊ticket(_nondeterministic_・_gap_等)を実ticketへ変換するのはルールの責務であり、
# 解決できなければworklog_lint.shが検知する。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <rules_file> < turns.json" >&2
  echo "  rules_file: ルールを1行1JSONで記述したJSONLファイル" >&2
  echo "example: cp ticket_guess_rules/ticket_guess_rules.template.jsonl ticket_guess_rules/ticket_guess_rules.jsonl" >&2
  echo "example: worklog_session_turns_list.sh 2026-08-24 none | $SCRIPT ticket_guess_rules/ticket_guess_rules.jsonl" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/worklog_session_turns_guess_ticket.py" "$@"
