#!/usr/bin/env bash
# Launch claude, always with --remote-control <session_name> (session_name =
# remote repo name if cwd is a git repo root, else cwd's basename).
#
# usage: claude_launch.sh <mode> [-- claude options/prompt...]
#     or: claude_launch.sh -- claude options/prompt...   (no mode: plain launch, no resume)
#
# mode is exactly one of:
#   today                  resume today's session for this directory if one
#                           exists (deterministic, via claude_session_today_find.sh),
#                           otherwise start a new one.
#   resume | -              resume any existing session via claude's own
#                           interactive session picker (-r). "-" is an alias
#                           for "resume", not a distinct mode.
#   new [session_name]     start a brand-new session; prompts for a name if
#                           not given.
#   <session_id>|<title_regex>
#                           resume that specific session directly (via
#                           claude_session_resolve.sh; must match exactly one
#                           session).
#
# Anything after a literal "--" is passed through to claude as-is (e.g. -p
# 'prompt'), in addition to whatever the mode above launches with.
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

function echo2() {
  echo "$1" >&2
}

function usage() {
  echo2 "$SCRIPT: $1"
  echo2 "usage: $SCRIPT <mode> [-- claude options/prompt...]"
  echo2 "  mode: today | resume | - | new [session_name] | <session_id> | <title_regex>"
  echo2 "example: $SCRIPT today                               # 今日このディレクトリで開いたセッションがあればresume、無ければ新規起動"
  echo2 "example: $SCRIPT resume                               # claude自身の対話式セッションピッカー(-r)を出す"
  echo2 "example: $SCRIPT -                                    # resume と同じ（別名）"
  echo2 "example: $SCRIPT new \"note記事の下書き整理\"              # 指定した名前で新規セッションを開始"
  echo2 "example: $SCRIPT 501c69e7-ffc3-497d-87f2-1ccd397242ab  # このsession_idのセッションを直接resume"
  echo2 "example: $SCRIPT 'imc'                                 # タイトルがこの正規表現に一意にマッチするセッションをresume"
  echo2 "example: $SCRIPT today -- -p 'some prompt'             # today起動しつつ、-pをclaudeにスルーパス"
  echo2 "example: $SCRIPT -- -p 'some prompt'                   # モード無し、resumeせずにそのままclaudeへスルーパス"
  exit 1
}

if [ "$#" -eq 0 ]; then
  usage "Expected at least one argument"
fi
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  usage "help requested"
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
   && [ "$(git rev-parse --show-toplevel)" = "$(pwd)" ]; then
  remote_url=$(git config --get remote.origin.url 2>/dev/null || true)
  if [ -n "$remote_url" ]; then
    session_name=$(basename "$remote_url" .git)
  else
    session_name=$(basename "$(pwd)")
  fi
else
  session_name=$(basename "$(pwd)")
fi

# No mode, just "-- <claude args>": plain launch, no resume/today logic at all.
if [ "$1" = "--" ]; then
  shift
  exec claude --remote-control "$session_name" "$@"
fi

mode="$1"
shift

new_name=""
if [ "$mode" = "new" ] && [ "$#" -gt 0 ] && [ "$1" != "--" ]; then
  new_name="$1"
  shift
fi

if [ "${1:-}" = "--" ]; then
  shift
elif [ "$#" -gt 0 ]; then
  usage "Unexpected argument '$1' (claudeへスルーパスする引数の前には -- を置いてください)"
fi
# remaining "$@" (possibly empty) = claude passthrough args

case "$mode" in
  today)
    today_session_id=$("$SCRIPT_DIR/claude_session_today_find.sh" "$(pwd)")
    if [ -n "$today_session_id" ]; then
      exec claude --resume "$today_session_id" --remote-control "$session_name" "$@"
    else
      exec claude --remote-control "$session_name" "$@"
    fi
    ;;
  resume|-)
    exec claude --remote-control "$session_name" -r "$@"
    ;;
  new)
    if [ -z "$new_name" ]; then
      read -r -p "新しいセッション名: " new_name >&2
    fi
    [ -n "$new_name" ] || usage "セッション名が空です"
    exec claude --remote-control "$session_name" -n "$new_name" "$@"
    ;;
  *)
    if ! resolved_session_id=$("$SCRIPT_DIR/claude_session_resolve.sh" "$mode"); then
      usage "'$mode' に一致するセッションが見つかりません（詳細は上記メッセージ参照）"
    fi
    exec claude --resume "$resolved_session_id" --remote-control "$session_name" "$@"
    ;;
esac
