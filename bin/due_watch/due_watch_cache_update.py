"""交換形式JSON(stdin)を _cache.json へ差分マージする。due_watch_cache_update.sh から呼ぶ。

- key = (source, id)。入力にあれば upsert(summary/deadline/url を更新、last_seen=now、
  first_seen は保持)。無ければ新規追加。
- 入力に含まれる source について、入力に無いキャッシュレコードは「消えた(対応済み・削除)」
  として除去する。入力に含まれない source のレコードは触らない(その source の fetch を
  今回回していないだけかもしれないため)。
- deadline が now より EXPIRE_GRACE(既定1日)以上前のレコードは期限切れとして除去。
"""

import json
import os
import sys
from datetime import timedelta

import due_watch_lib as lib

PROG = os.path.basename(__file__)
EXPIRE_GRACE = timedelta(days=1)


def fail(msg: str) -> None:
    print(f"{PROG}: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if sys.argv[1:]:
        fail("引数は取りません。usage: due_watch_cache_update.sh < exchange.json")

    try:
        incoming = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        fail(f"stdin のJSONを読めません: {e}")

    try:
        lib.validate_exchange(incoming)
    except ValueError as e:
        fail(f"交換形式が不正です: {e}")

    now_iso = lib.now_jst().isoformat(timespec="seconds")
    now = lib.now_jst()

    cache = lib.load_cache()
    by_key = {(r["source"], str(r["id"])): r for r in cache}

    incoming_sources = {r["source"] for r in incoming}
    incoming_keys = {(r["source"], str(r["id"])) for r in incoming}

    for r in incoming:
        key = (r["source"], str(r["id"]))
        existing = by_key.get(key)
        if existing is not None:
            existing["summary"] = r["summary"]
            existing["deadline"] = r["deadline"]
            existing["url"] = r["url"]
            existing["posted_at"] = r["posted_at"]
            existing["addressed_to_me"] = r["addressed_to_me"]
            existing["last_seen"] = now_iso
        else:
            by_key[key] = {
                "source": r["source"],
                "id": str(r["id"]),
                "summary": r["summary"],
                "deadline": r["deadline"],
                "url": r["url"],
                "posted_at": r["posted_at"],
                "addressed_to_me": r["addressed_to_me"],
                "first_seen": now_iso,
                "last_seen": now_iso,
            }

    removed_gone = 0
    removed_expired = 0
    kept = []
    for key, rec in by_key.items():
        if rec["source"] in incoming_sources and key not in incoming_keys:
            removed_gone += 1
            continue
        dl = lib.parse_deadline(rec["deadline"])
        if dl is not None and dl < now - EXPIRE_GRACE:
            removed_expired += 1
            continue
        kept.append(rec)

    kept.sort(key=lambda r: (r["deadline"] is None, r["deadline"] or "", r["source"], r["id"]))
    lib.save_cache(kept)

    src = ", ".join(sorted(incoming_sources)) or "(sourceなし)"
    print(
        f"{PROG}: {src}: 入力{len(incoming)}件 => upsert / 消滅除去{removed_gone} / "
        f"期限切れ除去{removed_expired} => キャッシュ{len(kept)}件 ({lib.CACHE_PATH})",
        file=sys.stderr,
    )
    print("次にすべきこと: due_watch_cache_show.sh tsv で一覧を確認してください", file=sys.stderr)


if __name__ == "__main__":
    main()
