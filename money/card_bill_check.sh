#!/bin/bash
# カード利用明細CSVをclaudeに検算させ、{sum, equal}のJSONを標準出力に返す
# usage: card_bill_check.sh <csv_file>
# example: card_bill_check.sh SAISON_2608.csv

set -eu

script_basename=$(basename "$0")

if [ "$#" -ne 1 ]; then
  {
    echo "${script_basename}: Wrong number of arguments"
    echo "usage: ${script_basename} <csv_file>"
    echo "example: ${script_basename} SAISON_2608.csv"
  } >&2
  exit 1
fi

csv_file="$1"

if [ ! -f "$csv_file" ]; then
  echo "${script_basename}: File not found: ${csv_file}" >&2
  exit 1
fi

now() {
  TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S(JST)'
}

echo "$(now) ${script_basename}: claudeに ${csv_file} の検算を依頼中... (数十秒かかることがあります)" >&2

set +e
claude -p --allowedTools "Read Bash(awk:*) Bash(python3:*)" <<EOF | cat
${csv_file}を検算できますか？{sum: 金額, equal: boolean} だけ出力してください。確認はすべてyesです。
EOF
result_status="${PIPESTATUS[0]}"
set -e

if [ "$result_status" -eq 0 ]; then
  echo "$(now) ${script_basename}: 完了 (exit ${result_status})。次に: 上記JSONの sum と equal を確認してください。" >&2
else
  echo "$(now) ${script_basename}: 失敗 (exit ${result_status})。次に: claude CLIの認証状態・ネットワークを確認し、再実行してください。" >&2
  exit "$result_status"
fi
