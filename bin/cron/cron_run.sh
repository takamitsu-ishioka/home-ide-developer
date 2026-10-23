#!/usr/bin/env bash
# crontab の各行が呼ぶラッパー。cron の最小環境を、このリポジトリの cron ジョブが必要とする
# 最小 env (bin/cron/cron.env、任意で bin/cron/_cron.env) へ揃えてから、渡されたコマンドを
# exec する。crond から呼ばれるので stdin は無い。
#
# 使い方(crontab 内):
#   */10 * * * * "$HOME/bin/cron/cron_run.sh" due_watch_poll.sh [args...]
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -lt 1 ]; then
  echo "$SCRIPT: Too few arguments" >&2
  echo "usage: $SCRIPT <command> [args...]" >&2
  echo "example: $SCRIPT due_watch_poll.sh" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/cron.env" ]; then
  echo "$SCRIPT: $SCRIPT_DIR/cron.env not found" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$SCRIPT_DIR/cron.env"
# マシン固有の上書き(任意)。無くてもよい。
# shellcheck disable=SC1091
[ -f "$SCRIPT_DIR/_cron.env" ] && source "$SCRIPT_DIR/_cron.env"
set +a

echo "$(date '+%Y-%m-%d %H:%M:%S %Z') $SCRIPT: exec $*" >&2
exec "$@"
