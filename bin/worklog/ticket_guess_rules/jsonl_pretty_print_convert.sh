#!/usr/bin/env bash
# 指定したファイルそれぞれにjsonl_pretty_print.sh(1行1JSON値のJSONLを整形して
# 標準出力するツール)をかけ、その出力を同じファイルへ書き戻す(jsonl_pretty_print.sh
# 自体はファイルを書き換えないstdoutフィルタなので、そこに「書き戻す」動作を足す薄いラッパー)。
# 複数ファイル(シェルのglobを含む)を一度に指定できる。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -eq 0 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <file>..." >&2
  echo "  file: 整形済みJSON値が連続するファイル(このファイル自体を書き換える。複数指定可)" >&2
  echo "example: $SCRIPT ticket_guess_rules.v1.jsonl" >&2
  echo "example: $SCRIPT *.jsonl" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/jsonl_pretty_print_convert.py" "$@"
