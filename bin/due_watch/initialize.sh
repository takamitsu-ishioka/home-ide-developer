#!/usr/bin/env bash
# due_watch を使い始めるための初期化(検査だけ。何も書き換えない)。冪等 — 何度でも。
#   1. python3 の確認
#   2. imc(~/imc、別repo)があり、Teams にログイン済みか(imc_teams_auth.sh status)
#   3. teams_channels.local.tsv のチャネルを imc も取得しているか(~/imc/teams_channels.local.tsv)
#   4. スモークテスト(due_watch_fetch_teams.sh)
# 2026-10-15 まであった Power Automate フロー・Google Drive の段は廃止した(design.md §5)。
# 定期実行は bin/cron/crontab(imc_fetch.sh の各経路と due_watch_poll.sh)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMC_DIR="$HOME/imc"

if [ "$#" -ne 0 ]; then
  echo "$SCRIPT: 引数は取りません" >&2
  echo "usage: $SCRIPT" >&2
  echo "example: $SCRIPT" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

step() { echo "$SCRIPT: $*" >&2; }
ng() { step "NG: $1"; echo "次にすべきこと: $2" >&2; exit 1; }

command -v python3 >/dev/null || ng "python3 がありません" "sudo apt install python3"
step "1/4 python3: OK"

[ -x "$IMC_DIR/imc_fetch.sh" ] || ng "$IMC_DIR に imc がありません" \
  "git clone git@github.com:takamitsu-ishioka/imc.git $IMC_DIR && $IMC_DIR/initialize.sh"
"$IMC_DIR/imc_teams_auth.sh" status >/dev/null 2>&1 || ng "imc が Teams にログインしていません" \
  "$IMC_DIR/imc_teams_auth.sh login"
step "2/4 imc・Teams ログイン: OK"

missing=$(grep -v -e '^#' -e '^[[:space:]]*$' "$SCRIPT_DIR/teams_channels.local.tsv" \
  | grep -v -x -F -f <(cat "$IMC_DIR/teams_channels.local.tsv" 2>/dev/null) || true)
[ -z "$missing" ] || ng "imc が取得していないチャネル: $(echo "$missing" | tr '\t\n' '/ ')" \
  "その行を $IMC_DIR/teams_channels.local.tsv に足し、$IMC_DIR/imc_teams_fetch.sh <7日前の日付> < その行 で一度取得する"
step "3/4 チャネル: OK"

n=$("$SCRIPT_DIR/due_watch_fetch_teams.sh" 2>/dev/null | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))') \
  || ng "due_watch_fetch_teams.sh が失敗しました" "$SCRIPT_DIR/due_watch_fetch_teams.sh を直接実行してエラーを見る"
step "4/4 due_watch_fetch_teams.sh: OK(交換形式 $n 件)"
echo "次にすべきこと: $SCRIPT_DIR/due_watch_poll.sh && $SCRIPT_DIR/due_watch_cache_show.sh tsv" >&2
