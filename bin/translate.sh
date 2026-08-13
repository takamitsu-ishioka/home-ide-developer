#!/bin/bash
# Markdown文書(stdin)を<src_lang>から<dst_lang>へ翻訳し、stdoutへ出力する。
# 実体は translate.py。claude -p を "## " 見出し単位のチャンクごとに呼び出し、
# 改行保存規約(行末のゼロ幅スペース+半角スペース2つ等)を含めた
# 行単位の構造を保ったまま翻訳する。
set -euo pipefail

BASENAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <src_lang> <dst_lang>"
    echo "example: $BASENAME ja en < README.ja.md > README.md"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 2 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

exec python3 "$SCRIPT_DIR/translate.py" "$1" "$2"
