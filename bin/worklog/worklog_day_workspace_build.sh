#!/usr/bin/env bash
# 指定日のセッションログから、turns抽出 => 正規化(regularize) => (参考情報として
# ルール更新案を生成) => ticket再分類 => ticket別セグメント化 => lint、の一連の
# 中間生成物を _workspace/<date>/ の下に作り、ticket_guess_rules_fileと合わせて
# VSCodeで開く(副作用は_workspace配下のファイル生成のみ)。
# ticket_guess_rules_fileが存在しない場合はnot foundで即エラー終了する(誤ったパス指定を
# 静かに新規ファイルへすり替えないため)。新しいルールファイルを作りたい場合は
# ticket_guess_rules/ticket_guess_rules.template.jsonlを手動でcopyしてから指定すること。
# 生成物はあくまで目視確認・修正用の作業ファイル。rules_fileを編集しながら
# worklog.linted.jsonが満足いく内容になるまで本スクリプトを再実行するのはユーザーの仕事。
# 満足したら、その内容をbin/worklog/log/<date>.jsonへ確定保存し、Jira投稿は
# instructions_to_ai_agent.mdの手順(人間の確認 => worklog_lint.sh => worklog_jira_post_batch.sh)に従う。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 2 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <date> <ticket_guess_rules_file>" >&2
  echo "  date                    : YYYY-MM-DD" >&2
  echo "  ticket_guess_rules_file : worklog_session_turns_guess_ticket.shへ渡すルールファイル(JSONL)" >&2
  echo "example: $SCRIPT 2026-08-26 ticket_guess_rules/ticket_guess_rules.jsonl" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

day="$1"
rules_file="$2"

if [ ! -f "$rules_file" ]; then
  echo "$SCRIPT: ticket_guess_rules_file not found: $rules_file" >&2
  echo "次にすべきこと: 新規作成するなら cp $SCRIPT_DIR/ticket_guess_rules/ticket_guess_rules.template.jsonl $rules_file を実行してから再実行してください" >&2
  exit 1
fi

workspace_dir="$SCRIPT_DIR/_workspace/$day"
mkdir -p "$workspace_dir"

"$SCRIPT_DIR/worklog_session_turns_list.sh" "$day" none \
  | json_pretty_print.sh > "$workspace_dir/turns.json"

"$SCRIPT_DIR/worklog_session_turns_regularize.sh" < "$workspace_dir/turns.json" \
  | json_pretty_print.sh > "$workspace_dir/turns.regularized.json"

suggested_rules_file="$SCRIPT_DIR/ticket_guess_rules/ticket_guess_rules.$(date +%Y%m%d%H%M%S).jsonl"
"$SCRIPT_DIR/worklog_guess_ticket_rules_update_suggest.sh" "$workspace_dir/turns.regularized.json" "$rules_file" \
  > "$suggested_rules_file"

"$SCRIPT_DIR/worklog_session_turns_guess_ticket.sh" "$rules_file" < "$workspace_dir/turns.regularized.json" \
  | json_pretty_print.sh > "$workspace_dir/turns.guessed.json"

"$SCRIPT_DIR/worklog_session_infer.sh" < "$workspace_dir/turns.guessed.json" \
  | json_pretty_print.sh > "$workspace_dir/worklog.json"

"$SCRIPT_DIR/worklog_lint.sh" < "$workspace_dir/worklog.json" \
  | json_pretty_print.sh > "$workspace_dir/worklog.linted.json"

vscode.sh "$workspace_dir"/*.json "$rules_file" "$suggested_rules_file"

echo "$SCRIPT: $workspace_dir/{turns,worklog,worklog.linted}.json を生成し、VSCodeで開きました" >&2
echo "$SCRIPT: ルール更新案を $suggested_rules_file に生成しました" >&2
echo "次にすべきこと: worklog.linted.jsonを目視確認してください。" >&2
echo "  ルール更新案の中で使えそうな行だけ $rules_file へ反映し、本スクリプトを再実行してください。" >&2
echo "  満足したらbin/worklog/log/$day.jsonへ確定保存してください" >&2
