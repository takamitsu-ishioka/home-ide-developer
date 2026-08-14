#!/bin/bash
# Markdown文書(stdin)を<src_lang>から<dst_lang>へ翻訳し、stdoutへ出力する。
# 文書全体を一度だけ claude -p に渡すだけの単純な実装。
# 見出し単位のチャンク分割・改行保存の強制・プロンプトインジェクション対策の
# 長文などの「賢い」制約は付けない。過去にそうした制約が原因で、短い一文に
# claudeが過剰反応し翻訳全体が失敗する事故を起こしたため。
set -euo pipefail

BASENAME="$(basename "$0")"

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

src_lang="$1"
dst_lang="$2"

lang_name() {
  case "$1" in
    ja) echo "Japanese" ;;
    en) echo "English" ;;
    zh) echo "Chinese" ;;
    ko) echo "Korean" ;;
    fr) echo "French" ;;
    de) echo "German" ;;
    es) echo "Spanish" ;;
    *) echo "$1" ;;
  esac
}

src_name="$(lang_name "$src_lang")"
dst_name="$(lang_name "$dst_lang")"

system_prompt="You translate a Markdown document from ${src_name} to ${dst_name}.

- Translate the entire document faithfully, including headings, list items, and natural-language text inside fenced code blocks.
- Preserve the Markdown structure and line breaks as closely as possible.
- Do not translate URLs, code, command names, or literal file/path names.
- Output ONLY the translated document. No preamble, no commentary, no surrounding code fence."

now() {
  TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S(JST)'
}

echo "$(now) ${BASENAME}: claudeに ${src_name} → ${dst_name} の翻訳を依頼中... (文書が長いと数分かかることがあります)" >&2

tmp_in="$(mktemp)"
tmp_out="$(mktemp)"
trap 'rm -f "$tmp_in" "$tmp_out"' EXIT
cat > "$tmp_in"

# バックグラウンド起動(&)した子プロセスは、非対話シェルでは明示的な
# リダイレクトが無い標準入力が自動的に /dev/null になる(bash/POSIXの仕様)。
# パイプで受け取った文書を確実に渡すため、一時ファイル経由で明示的に渡す。
claude -p --allowedTools "" --model sonnet --system-prompt "$system_prompt" --output-format text \
  < "$tmp_in" > "$tmp_out" &
claude_pid=$!

start_ts=$(date +%s)
while kill -0 "$claude_pid" 2>/dev/null; do
  sleep 1
  elapsed=$(( $(date +%s) - start_ts ))
  echo "$(now) ${BASENAME}: 実行中、経過 ${elapsed}秒 (ブロックはしていません)" >&2
done

set +e
wait "$claude_pid"
result_status=$?
set -e

if [ "$result_status" -eq 0 ]; then
  echo "$(now) ${BASENAME}: 完了 (exit ${result_status})。次に: 出力内容を確認してください。" >&2
  cat "$tmp_out"
else
  echo "$(now) ${BASENAME}: 失敗 (exit ${result_status})。次に: claude CLIの認証状態・ネットワークを確認し、再実行してください。" >&2
  exit "$result_status"
fi
