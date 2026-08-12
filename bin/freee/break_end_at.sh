#!/usr/bin/env bash
# 指定時刻に at コマンドで time_clock_punch.sh break_end TODAY(休憩終了の打刻)を1回だけ予約する
# at/atd のインストール・起動が前提(sudo apt install -y at && sudo systemctl enable --now atd)
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

valid_args=1
if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
  valid_args=0
else
  for extra_arg in "${@:2}"; do
    case "$extra_arg" in
      --dry-run|--confirm) ;;
      *) valid_args=0 ;;
    esac
  done
  if [ "$#" -eq 3 ] && [ "${2}" = "${3}" ]; then
    valid_args=0
  fi
fi

if [ "$valid_args" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <at_time> [--dry-run] [--confirm]" >&2
  echo "  at_time: at コマンドに渡す時刻指定(例: 13:40, now + 5 minutes)" >&2
  echo "  --dry-run と --confirm は独立したオプション(併用可、順不同):" >&2
  echo "    --dry-run: 実際には at に予約せず、予約内容のみ表示する" >&2
  echo "    --confirm: 予約前に(Y/n)で確認を求める(--dry-runの有無に関わらず)。指定しない場合、確認なしで即座に予約する" >&2
  echo "example: $SCRIPT 13:40" >&2
  echo "example: $SCRIPT 13:40 --dry-run" >&2
  echo "example: $SCRIPT 'now + 5 minutes' --confirm" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

at_time="$1"
dry_run=0
confirm=0
for arg in "${@:2}"; do
  case "$arg" in
    --dry-run) dry_run=1 ;;
    --confirm) confirm=1 ;;
  esac
done

log_file="$SCRIPT_DIR/time_clock_punch.log"
punch_cmd="\"$SCRIPT_DIR/time_clock_punch.sh\" break_end TODAY >> \"$log_file\" 2>&1"

echo "$SCRIPT: 以下の内容で at に予約します" >&2
echo "  時刻      : $at_time" >&2
echo "  コマンド  : $punch_cmd" >&2
echo "  ログ出力先: $log_file" >&2

if [ "$confirm" -eq 1 ]; then
  read -r -p "$SCRIPT: 予約してよろしいですか? (Y/n) " reply
  case "$reply" in
    [nN]*)
      echo "$SCRIPT: キャンセルしました" >&2
      exit 1
      ;;
  esac
fi

if [ "$dry_run" -eq 1 ]; then
  echo "$SCRIPT: --dry-run のため実際には予約しません" >&2
  exit 0
fi

echo "$punch_cmd" | at "$at_time"
