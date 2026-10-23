#!/usr/bin/env bash
# bin/cron/crontab をこのマシンの user crontab として登録する(全置換)。
# 「このマシンの crontab は repo が所有」— 既存の手動エントリは失われる。
# WSL では crond が自動起動しないので、登録後に稼働状況も確認する(起動はしない)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRONTAB_FILE="$SCRIPT_DIR/crontab"

dry_run=0
confirm=0
for a in "$@"; do
  case "$a" in
    --dry-run) dry_run=1 ;;
    --confirm) confirm=1 ;;
    *)
      echo "$SCRIPT: Invalid option: $a" >&2
      echo "usage: $SCRIPT [--dry-run] [--confirm]" >&2
      echo "  (引数なし: 確認なしで登録 / --dry-run: 差分表示のみ / --confirm: 登録前に y/n)" >&2
      echo "example: $SCRIPT --dry-run" >&2
      awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
      exit 1
      ;;
  esac
done

if [ ! -f "$CRONTAB_FILE" ]; then
  echo "$SCRIPT: $CRONTAB_FILE not found" >&2
  exit 1
fi

current=$(crontab -l 2>/dev/null || true)

echo "入出力:" >&2
echo "  読み取り (新crontab): $CRONTAB_FILE" >&2
echo "  上書き (user crontab): $(id -un) @ $(hostname)" >&2
echo >&2
echo "--- 現 user crontab => bin/cron/crontab の差分 ---" >&2
if command -v diff >/dev/null 2>&1; then
  diff <(printf '%s\n' "$current") "$CRONTAB_FILE" >&2 && echo "(差分なし)" >&2 || true
else
  echo "(diff コマンドが無いため差分表示をスキップ)" >&2
fi
echo >&2

active_jobs=$(grep -cE '^[^#[:space:]]' "$CRONTAB_FILE" || true)
echo "$SCRIPT: 登録後の有効ジョブ行数: $active_jobs" >&2

if [ "$dry_run" -eq 1 ]; then
  echo "$SCRIPT: --dry-run のため登録しません" >&2
  exit 0
fi

if [ "$confirm" -eq 1 ]; then
  printf 'この内容で user crontab を全置換します。よろしいですか? [y/N] ' >&2
  read -r ans
  case "$ans" in
    y | Y | yes | YES) ;;
    *)
      echo "$SCRIPT: 中止しました" >&2
      exit 1
      ;;
  esac
fi

crontab "$CRONTAB_FILE"
echo "$SCRIPT: user crontab を bin/cron/crontab で全置換しました" >&2

# crond の稼働確認(WSL では手動起動が要る)
if pgrep -x cron >/dev/null 2>&1 || pgrep -x crond >/dev/null 2>&1; then
  echo "$SCRIPT: crond 稼働中" >&2
else
  echo "$SCRIPT: 警告: crond が稼働していません。ジョブは実行されません" >&2
  echo "次にすべきこと: sudo service cron start (WSL) で起動してください" >&2
  exit 1
fi

echo "次にすべきこと: crontab -l で登録内容を確認してください" >&2
