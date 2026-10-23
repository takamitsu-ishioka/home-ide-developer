"""_cache.json を読み、deadline の近い順に一覧を出力する(読み取り専用)。
due_watch_cache_show.sh から呼ぶ。

deadline_bucket は保存された値ではなく、実行時の now を基準にその場で算出する
(バケットは時間相対なので、キャッシュに固定して持たない)。
"""

import json
import os
import sys

import due_watch_lib as lib

PROG = os.path.basename(__file__)


def fail(msg: str) -> None:
    print(f"{PROG}: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in ("tsv", "json"):
        fail("usage: due_watch_cache_show.sh <tsv|json>")
    fmt = args[0]

    now = lib.now_jst()
    rows = []
    for r in lib.load_cache():
        dl = lib.parse_deadline(r["deadline"])
        rows.append(
            {
                "posted_at": r.get("posted_at"),
                "addressed_to_me": bool(r.get("addressed_to_me")),
                "deadline_bucket": lib.deadline_bucket(dl, now),
                "deadline": r["deadline"],
                "source": r["source"],
                "id": r["id"],
                "summary": r["summary"],
                "url": r["url"],
            }
        )

    # 同じ(deadline_bucket, deadline)内では posted_at の新しい順にしたいので、
    # 先に posted_at 降順で安定ソートしてから、主キー(bucket, deadline)で安定ソートする。
    rows.sort(key=lambda x: x["posted_at"] or "", reverse=True)
    rows.sort(
        key=lambda x: (
            lib.BUCKET_ORDER.get(x["deadline_bucket"], 99),
            x["deadline"] or "9999-12-31",
        )
    )

    if fmt == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for x in rows:
            summary = x["summary"].replace("\t", " ").replace("\n", " ")
            print(
                "\t".join(
                    [
                        x["posted_at"] or "-",
                        "true" if x["addressed_to_me"] else "false",
                        x["deadline_bucket"],
                        x["deadline"] or "-",
                        x["source"],
                        summary,
                        x["url"] or "-",
                    ]
                )
            )

    print(f"{PROG}: {len(rows)}件", file=sys.stderr)


if __name__ == "__main__":
    main()
