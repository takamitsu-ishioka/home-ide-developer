#!/bin/bash
# Translate a Markdown document (stdin) from <src_lang> to <dst_lang>, writing
# to stdout. Simple implementation: the whole document is sent to claude -p
# in one shot. No "clever" constraints such as per-heading chunking, forced
# line-break preservation, or a long prompt-injection-defense system prompt.
# An earlier version had those, and they caused claude to overreact to a
# single short sentence and fail the whole translation.
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

echo "$(now) ${BASENAME}: asking claude to translate ${src_name} -> ${dst_name}... (can take a few minutes for long documents)" >&2

tmp_in="$(mktemp)"
tmp_out="$(mktemp)"
trap 'rm -f "$tmp_in" "$tmp_out"' EXIT
cat > "$tmp_in"

# A backgrounded (&) child process, in a non-interactive shell, has its
# standard input redirected to /dev/null unless explicitly redirected
# (bash/POSIX behavior). To make sure the piped-in document actually
# reaches claude, pass it explicitly via a temp file.
claude -p --allowedTools "" --model sonnet --system-prompt "$system_prompt" --output-format text \
  < "$tmp_in" > "$tmp_out" &
claude_pid=$!

start_ts=$(date +%s)
while kill -0 "$claude_pid" 2>/dev/null; do
  sleep 1
  elapsed=$(( $(date +%s) - start_ts ))
  echo "$(now) ${BASENAME}: still running, elapsed ${elapsed}s (not blocked)" >&2
done

set +e
wait "$claude_pid"
result_status=$?
set -e

if [ "$result_status" -eq 0 ]; then
  echo "$(now) ${BASENAME}: done (exit ${result_status}). Next: review the translated output." >&2
  cat "$tmp_out"
else
  echo "$(now) ${BASENAME}: failed (exit ${result_status}). Next: check claude CLI auth/network and retry." >&2
  exit "$result_status"
fi
