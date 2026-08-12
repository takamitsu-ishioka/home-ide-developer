#!/usr/bin/env bash
# freee人事労務APIで指定日の勤怠タグ(回数タグ)を1個、指定した回数に設定する
# このAPIのPUTは指定日の全タグを上書きする仕様のため、既存タグを事前取得してマージしてから送信する
# (指定したタグ以外は、その日に既に設定されている回数のまま維持される)
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

valid_args=1
if [ "$#" -lt 3 ] || [ "$#" -gt 5 ]; then
  valid_args=0
else
  for extra_arg in "${@:4}"; do
    case "$extra_arg" in
      --dry-run|--confirm) ;;
      *) valid_args=0 ;;
    esac
  done
  if [ "$#" -eq 5 ] && [ "${4}" = "${5}" ]; then
    valid_args=0
  fi
fi

if [ "$valid_args" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <date> <tag_name> <amount> [--dry-run] [--confirm]" >&2
  echo "  date    : TODAY(当日) または対象年月日(YYYY-MM-DD)" >&2
  echo "  tag_name: 勤怠タグの名称(完全一致。事業所の勤怠タグ設定に登録済みのもの。例:自宅)" >&2
  echo "  amount  : 設定する回数(0以上の整数。チェックを付ける=1、外す=0)" >&2
  echo "  --dry-run と --confirm は独立したオプション(併用可、順不同):" >&2
  echo "    --dry-run: 実際には更新せず、送信予定の内容のみ表示する" >&2
  echo "    --confirm: 実行前に(Y/n)で確認を求める(--dry-runの有無に関わらず)。指定しない場合、確認なしで即座に進む" >&2
  echo "example: $SCRIPT TODAY 自宅 1" >&2
  echo "example: $SCRIPT TODAY 自宅 1 --dry-run" >&2
  echo "example: $SCRIPT 2026-08-04 自宅 0 --confirm" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

ENV_FILE="${FREEE_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 "$SCRIPT_DIR/attendance_tag_set.py" "$@"
