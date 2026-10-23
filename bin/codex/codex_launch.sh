#!/usr/bin/env bash
# Launch codex, with the same mode design as claude_launch.sh.
#
# codex has no equivalent of claude's --remote-control (a session label), so
# that part isn't ported. It also has no -n (name a session at creation), so
# "new" still takes an optional initial prompt, not a name (same as before).
#
# usage: codex_launch.sh <mode> [-- codex options/prompt...]
#     or: codex_launch.sh -- codex options/prompt...   (no mode: plain launch, no resume)
#
# mode is exactly one of:
#   today                  resume today's session for this directory if one
#                           exists (deterministic, via codex_session_today_find.sh),
#                           otherwise start a new one.
#   resume | -              resume any existing session via codex's own
#                           interactive picker (`codex resume`). "-" is an
#                           alias for "resume", not a distinct mode.
#   new [initial_prompt]   start a brand-new session, optionally with an
#                           initial prompt.
#   <session_id>|<title_regex>
#                           resume that specific session directly (via
#                           codex_session_resolve.sh; must match exactly one
#                           session).
#
# Anything after a literal "--" is passed through to codex as-is (e.g.
# --search), in addition to whatever the mode above launches with.
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

function echo2() {
  echo "$1" >&2
}

function usage() {
  echo2 "$SCRIPT: $1"
  echo2 "usage: $SCRIPT <mode> [-- codex options/prompt...]"
  echo2 "  mode: today | resume | - | new [initial_prompt] | <session_id> | <title_regex>"
  echo2 "example: $SCRIPT today                               # 今日このディレクトリで開いたセッションがあればresume、無ければ新規起動"
  echo2 "example: $SCRIPT resume                               # codex自身の対話式セッションピッカー(codex resume)を出す"
  echo2 "example: $SCRIPT -                                    # resume と同じ（別名）"
  echo2 "example: $SCRIPT new \"note記事の下書き整理\"              # 最初のプロンプトを渡して新規セッションを開始"
  echo2 "example: $SCRIPT 501c69e7-ffc3-497d-87f2-1ccd397242ab  # このsession_idのセッションを直接resume"
  echo2 "example: $SCRIPT 'imc'                                 # タイトルがこの正規表現に一意にマッチするセッションをresume"
  echo2 "example: $SCRIPT today -- --search                     # today起動しつつ、--searchをcodexにスルーパス"
  echo2 "example: $SCRIPT -- --search                           # モード無し、resumeせずにそのままcodexへスルーパス"
  exit 1
}

if [ "$#" -eq 0 ]; then
  usage "Expected at least one argument"
fi
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  usage "help requested"
fi

# No mode, just "-- <codex args>": plain launch, no resume/today logic at all.
if [ "$1" = "--" ]; then
  shift
  exec codex "$@"
fi

mode="$1"
shift

initial_prompt=""
if [ "$mode" = "new" ] && [ "$#" -gt 0 ] && [ "$1" != "--" ]; then
  initial_prompt="$1"
  shift
fi

if [ "${1:-}" = "--" ]; then
  shift
elif [ "$#" -gt 0 ]; then
  usage "Unexpected argument '$1' (codexへスルーパスする引数の前には -- を置いてください)"
fi
# remaining "$@" (possibly empty) = codex passthrough args

case "$mode" in
  today)
    today_session_id=$("$SCRIPT_DIR/codex_session_today_find.sh" "$(pwd)")
    if [ -n "$today_session_id" ]; then
      exec codex resume "$today_session_id" "$@"
    else
      exec codex "$@"
    fi
    ;;
  resume|-)
    exec codex resume "$@"
    ;;
  new)
    if [ -n "$initial_prompt" ]; then
      exec codex "$initial_prompt" "$@"
    else
      exec codex "$@"
    fi
    ;;
  *)
    if ! resolved_session_id=$("$SCRIPT_DIR/codex_session_resolve.sh" "$mode"); then
      usage "'$mode' に一致するセッションが見つかりません（詳細は上記メッセージ参照）"
    fi
    exec codex resume "$resolved_session_id" "$@"
    ;;
esac
