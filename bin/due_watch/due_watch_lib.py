"""due_watch 共有モジュール。

- 交換形式レコード(fetchスクリプトの出力)の検証
- deadline_bucket の算出(表示用の相対バケット)
- _cache.json の読み書き

このモジュールは単体実行しない(.shラッパーも持たない)。
due_watch_cache_update.py / due_watch_cache_show.py 等が import する。
"""

import json
import os
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cache.json")

SOURCES = ("gmail", "outlook", "teams")

# 交換形式(fetchスクリプトの出力する1レコード)の必須キー。deadline と url と posted_at は null 可。
#   source        : "gmail" | "outlook" | "teams"
#   id            : 発信元システムでの一意識別子(文字列)
#   summary       : 件名・要約(1行想定)
#   deadline      : 期限。ISO8601(Asia/Tokyo)。無ければ null
#   url           : 元メッセージ・招待への deep link。取れなければ null
#   posted_at     : 投稿・作成日時。ISO8601(Asia/Tokyo)。取れなければ null
#   addressed_to_me: 自分宛(メンション等)と判定できたか。bool(取れない場合は false)
EXCHANGE_KEYS = ("source", "id", "summary", "deadline", "url", "posted_at", "addressed_to_me")

# deadline がこの範囲内(または期限切れ)なら "今"。act now を促すための閾値。定数。
IMMINENT = timedelta(hours=3)

# 表示順(ソート用)。design.md の列挙 + 遠い側の受け皿 "それ以降"。
BUCKET_ORDER = {
    "今": 0,
    "今日": 1,
    "今日+1": 2,
    "今日+2": 3,
    "今日+3": 4,
    "今日+4": 5,
    "今日+5": 6,
    "今日+6": 7,
    "来月末": 8,
    "それ以降": 9,
    "なし": 10,
}


def now_jst() -> datetime:
    return datetime.now(JST)


def parse_deadline(value):
    """ISO8601文字列 or None を、tz-aware(JST)の datetime or None にする。
    naive な文字列は JST とみなす。形式不正なら ValueError。
    """
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt.astimezone(JST)


def _last_moment_of_next_month(ref: datetime) -> datetime:
    """ref の翌月の末日 23:59:59 (JST)。"""
    y = ref.year + (1 if ref.month == 12 else 0)
    m = 1 if ref.month == 12 else ref.month + 1
    # 翌々月の1日 - 1秒
    ny = y + (1 if m == 12 else 0)
    nm = 1 if m == 12 else m + 1
    return datetime(ny, nm, 1, tzinfo=JST) - timedelta(seconds=1)


def deadline_bucket(deadline, now=None) -> str:
    """deadline(datetime or None)を表示用バケットへ。

    なし        : deadline が null
    今          : 期限切れ、または IMMINENT(既定3時間)以内
    今日        : 今日中(暦日、JST)
    今日+1..+6  : N日後
    来月末      : +7日以降で、翌月末までに収まる
    それ以降    : それより先
    """
    if deadline is None:
        return "なし"
    if now is None:
        now = now_jst()
    if deadline <= now + IMMINENT:
        return "今"
    delta_days = (deadline.date() - now.date()).days
    if delta_days == 0:
        return "今日"
    if 1 <= delta_days <= 6:
        return f"今日+{delta_days}"
    if deadline <= _last_moment_of_next_month(now):
        return "来月末"
    return "それ以降"


def validate_exchange(records) -> None:
    """交換形式レコード配列(JSON array)を検証する。問題があれば ValueError。"""
    if not isinstance(records, list):
        raise ValueError("交換形式はレコードの配列(JSON array)である必要があります")
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            raise ValueError(f"[{i}] レコードがオブジェクトではありません")
        for k in EXCHANGE_KEYS:
            if k not in r:
                raise ValueError(f"[{i}] 必須キー {k!r} がありません")
        if r["source"] not in SOURCES:
            raise ValueError(f"[{i}] source={r['source']!r} は {SOURCES} のいずれか")
        if not str(r["id"]):
            raise ValueError(f"[{i}] id が空です")
        try:
            parse_deadline(r["deadline"])
        except ValueError as e:
            raise ValueError(f"[{i}] deadline={r['deadline']!r} を解釈できません: {e}") from e
        try:
            parse_deadline(r["posted_at"])
        except ValueError as e:
            raise ValueError(f"[{i}] posted_at={r['posted_at']!r} を解釈できません: {e}") from e
        if not isinstance(r["addressed_to_me"], bool):
            raise ValueError(f"[{i}] addressed_to_me={r['addressed_to_me']!r} は bool である必要があります")


def load_cache() -> list:
    if not os.path.exists(CACHE_PATH):
        return []
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_cache(records: list) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
        f.write("\n")
