#!/usr/bin/env bash
# due_watch の _cache.json を、期限(deadline)の近い順に一覧表示する(読み取り専用)。
# deadline_bucket(今 / 今日 / 今日+N / 来月末 / それ以降 / なし)は実行時刻を基準に算出。
# format は tsv か json。tsv の列: posted_at, addressed_to_me, deadline_bucket, deadline, source, summary, url
# 同一(deadline_bucket, deadline)内は posted_at の新しい順。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 1 ] || { [ "$1" != "tsv" ] && [ "$1" != "json" ]; }; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <tsv|json>" >&2
  echo "example: $SCRIPT tsv" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/due_watch_cache_show.py" "$1"
