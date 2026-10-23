#!/usr/bin/env bash
# cron ジョブのログを日ごとに切り替え、古いものを消す(2026-10-16)。
#   1. 各 <log> を <log>.<YYYY-MM-DD>(今日の日付)へ移す。同じ日に2回動いたら追記する
#   2. <log>.<YYYY-MM-DD> のうち、日付が <keep_days> 日より前のものを消す
# ジョブは毎回 `>> <log>` で開き直すので、移したあとの書き込みは新しい <log> に入る。
# この PC は毎晩止まるので、夜中ではなく日中に cron から1日1回呼ぶ(bin/cron/crontab)。
# 中身が空のログは移さない(動いていないジョブの空ファイルを日付つきで増やさない)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")

usage() {
  echo "$SCRIPT: $1" >&2
  echo "usage: $SCRIPT <keep_days> <log> [<log> ...] [--dry-run]" >&2
  echo "  keep_days : 何日分の日付つきログを残すか(正の整数)" >&2
  echo "  log       : 切り替えるログファイル(複数可。glob で渡してよい)" >&2
  echo "  --dry-run : 任意。何も変えず、行うことだけを表示する" >&2
  echo "example: $SCRIPT 7 \$HOME/bin/due_watch/_*.log --dry-run" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
}

dry_run=false
args=()
for a in "$@"; do
  case "$a" in
    --dry-run) dry_run=true ;;
    -*) usage "Unknown option: $a" ;;
    *) args+=("$a") ;;
  esac
done
[ "${#args[@]}" -lt 2 ] && usage "Too few arguments"
keep="${args[0]}"
[[ "$keep" =~ ^[1-9][0-9]*$ ]] || usage "keep_days must be a positive integer: $keep"
logs=("${args[@]:1}")

today=$(date +%F)
cutoff=$(date -d "$keep days ago" +%F)
run() { if "$dry_run"; then echo "  (dry-run) $*" >&2; else "$@"; fi; }

echo "$SCRIPT: $today に切り替え、$cutoff より前の日付つきログを消す $($dry_run && echo --dry-run)" >&2
for log in "${logs[@]}"; do
  if [ ! -e "$log" ]; then
    echo "$SCRIPT: $log がありません(スキップ)" >&2
    continue
  fi
  dest="$log.$today"
  if [ -s "$log" ]; then
    if [ -e "$dest" ]; then
      if "$dry_run"; then echo "  (dry-run) $log を $dest に追記して空にする" >&2
      else cat "$log" >> "$dest" && : > "$log"; fi
    else
      run mv "$log" "$dest"
    fi
    echo "$SCRIPT: $log -> $dest" >&2
  fi
  for old in "$log".????-??-??; do
    [ -e "$old" ] || continue
    d="${old##*.}"
    if [[ "$d" < "$cutoff" ]]; then
      run rm -f "$old"
      echo "$SCRIPT: 削除 $old" >&2
    fi
  done
done
echo "次にすべきこと: 何もしなくてよい(cron が毎日呼ぶ)。古いログを見るなら ls ${logs[0]}.*" >&2
