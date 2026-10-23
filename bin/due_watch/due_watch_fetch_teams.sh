#!/usr/bin/env bash
# imc(~/imc、別repo)が取得済みの Teams メッセージのうち、teams_channels.local.tsv に挙げた
# チャネルの直近7日分を、交換形式のJSON配列にして stdout へ出す(読み取り専用)。
# Teams そのものには触らない: 取得は imc の仕事(cron の imc_fetch.sh teams)、
# due_watch はその結果を読んでキャッシュへ渡すだけ(分担は design.md §5)。
# 2026-10-15 に Power Automate → Google Drive(G:)経由の取り込みから置き換えた。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMC_DIR="$HOME/imc"

if [ "$#" -ne 0 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT" >&2
  echo "example: $SCRIPT | due_watch_cache_update.sh" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi
if [ ! -x "$IMC_DIR/imc_mail_list.sh" ]; then
  echo "$SCRIPT: $IMC_DIR/imc_mail_list.sh がありません" >&2
  echo "次にすべきこと: git clone git@github.com:takamitsu-ishioka/imc.git $IMC_DIR して imc の initialize.sh を実行してください" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/due_watch_fetch_teams.py" "$IMC_DIR"
