#!/usr/bin/env bash
# 指定したturns(regularize済みJSON)と現行のticket_guess_rules(JSONL)から、
# "_nondeterministic_"を実ticketへ解決するルール更新案(既存ルール+新規ルール、JSONL)を
# 標準出力へ返す(読み取り専用、ファイルは書き換えない。呼び出し側で新規ファイルへ
# リダイレクトし、目視確認の上で反映する運用を想定)。
# LLM(claude subagent等)は一切呼ばない。キーワード抽出(正規表現でカタカナ・漢字・英数字の
# 連続を抽出)とticket概要との文字bigram Jaccard類似度という、決定的でローカル完結の
# ヒューリスティックのみで候補を提案する(形態素解析器・embedding APIも不要)。
# 類似度の下限はbin/worklog/config.jsonのrule_generator.threshold_minで指定する。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 2 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <turns_file> <rules_file>" >&2
  echo "  turns_file: worklog_session_turns_regularize.shの出力(JSON)" >&2
  echo "  rules_file: 現行のticket_guess_rules(JSONL)" >&2
  echo "example: $SCRIPT _workspace/2026-08-26/turns.regularized.json ticket_guess_rules/ticket_guess_rules.v2.jsonl > ticket_guess_rules/ticket_guess_rules.\$(now | cut -d' ' -f1 | tr -d '-').jsonl" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/worklog_guess_ticket_rules_update_suggest.py" "$@"
