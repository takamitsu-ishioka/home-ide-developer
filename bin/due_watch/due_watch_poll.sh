#!/usr/bin/env bash
# fetch スクリプト群を順に実行し、出力(交換形式JSON配列)を1つに連結して
# due_watch_cache_update.sh へ渡す。cron から cron_run.sh 経由で10分毎に叩く想定。非対話。
#
# あるfetchが失敗(exit != 0)したら、その source は今回スキップする。理由: 失敗した source を
# 「空」として cache_update へ渡すと、その source の既存レコードが全部「消滅除去」されてしまう。
# fetch が成功して 0 件([])なら、それは正当な「今その source に案件なし」なので通す。
#
# 副作用: _cache.json の更新のみ。カレンダー変更等の副作用ゲートのある処理は含めない。
set -uo pipefail  # -e は付けない(1つのfetch失敗で全体を止めない)

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 0 ]; then
  echo "$SCRIPT: 引数は取りません" >&2
  echo "usage: $SCRIPT" >&2
  echo "example: cron_run.sh $SCRIPT" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

# 実装済みの fetch スクリプト。増えたらここに追加する。
FETCHERS=(
  due_watch_fetch_teams.sh
)

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

ok_files=()
failed=0
for f in "${FETCHERS[@]}"; do
  if out=$("$SCRIPT_DIR/$f" 2>"$tmp/$f.err"); then
    printf '%s' "$out" >"$tmp/$f.json"
    ok_files+=("$tmp/$f.json")
    [ -s "$tmp/$f.err" ] && cat "$tmp/$f.err" >&2
  else
    rc=$?
    failed=$((failed + 1))
    echo "$SCRIPT: $f が失敗(exit $rc)。この source は今回スキップします" >&2
    [ -s "$tmp/$f.err" ] && cat "$tmp/$f.err" >&2
  fi
done

# 成功した fetch の配列を連結(jq は使わない)
merged=$(python3 -c '
import json, sys
out = []
for p in sys.argv[1:]:
    out.extend(json.load(open(p, encoding="utf-8")))
print(json.dumps(out, ensure_ascii=False))
' "${ok_files[@]}")

printf '%s' "$merged" | "$SCRIPT_DIR/due_watch_cache_update.sh"
update_rc=$?

echo "$SCRIPT: fetch ${#FETCHERS[@]}本中 成功$(( ${#FETCHERS[@]} - failed )) / 失敗$failed" >&2
if [ "$failed" -gt 0 ]; then
  echo "次にすべきこと: 失敗した fetch の .env / 接続先を確認してください" >&2
fi
exit "$update_rc"
