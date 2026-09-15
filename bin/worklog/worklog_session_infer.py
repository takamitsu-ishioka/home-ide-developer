import json
import os
import sys
from datetime import datetime

import worklog_jira_api

PROG = os.path.basename(__file__)
DEFAULT_TICKET = "GENERAL-451"  # cwd => ticket が解決できない場合等の受け皿(その他の雑多な作業)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def duration_hm(start_hm: str, end_hm: str) -> str:
    """start/end(共に"HH:MM")の表示文字列から計算する。begin/endの生timestampの秒数を
    使うと、表示上のHH:MMから素朴に引き算した値とズレることがある(例: 14:44:50〜16:16:10は
    表示上92分に見えるが実際は91分)ため、常に表示文字列を単一の真実として計算する。
    """
    start = datetime.strptime(start_hm, "%H:%M")
    end = datetime.strptime(end_hm, "%H:%M")
    minutes = int((end - start).total_seconds() // 60)
    return f"{minutes // 60}:{minutes % 60:02d}"


def segment_note(turns: list[dict], ticket: str) -> str:
    """セグメント内の最初の非空userセリフをnoteの初期値とする(無ければ空、GENERAL-451なら定型文)。"""
    for turn in turns:
        for line in turn.get("user", []):
            if line:
                return line
    return "その他の雑多な作業" if ticket == DEFAULT_TICKET else ""


def build_segments(turns: list[dict]) -> list[tuple[str, str, datetime, datetime, list[dict]]]:
    """(repo, ticket)が連続する区間をまとめる。

    freeeの打刻は使わない。1日の外枠は、その日のturns自体の最初〜最後のtimestampになる
    (最初のセグメントの開始は最初のturn自身の応答完了時刻であり、それ以前の実働は含まれない)。
    """
    segments: list[tuple[str, str, datetime, datetime, list[dict]]] = []
    current_repo: str | None = None
    current_ticket: str | None = None
    current_turns: list[dict] = []
    begin_ts: datetime | None = None

    for turn in turns:
        ts = datetime.fromisoformat(turn["timestamp"])
        repo = turn.get("repo", "none")
        ticket = turn.get("ticket", DEFAULT_TICKET)

        if current_ticket is None:
            current_repo, current_ticket, begin_ts, current_turns = repo, ticket, ts, [turn]
            continue

        if (repo, ticket) != (current_repo, current_ticket):
            segments.append((current_repo, current_ticket, begin_ts, ts, current_turns))
            current_repo, current_ticket, begin_ts, current_turns = repo, ticket, ts, [turn]
        else:
            current_turns.append(turn)

    if current_turns:
        end_ts = datetime.fromisoformat(current_turns[-1]["timestamp"])
        segments.append((current_repo, current_ticket, begin_ts, end_ts, current_turns))

    return [s for s in segments if s[3] > s[2]]


def to_record(date_text: str, repo: str, ticket: str, begin: datetime, end: datetime, turns: list[dict]) -> dict:
    start_hm = begin.strftime("%H:%M")
    end_hm = end.strftime("%H:%M")
    return {
        "date": date_text,
        "start": start_hm,
        "end": end_hm,
        "duration": duration_hm(start_hm, end_hm),
        "repo": repo,
        "ticket": ticket,
        "ticket_url": f"{worklog_jira_api.JIRA_BASE_URL}/browse/{ticket}",
        "note": segment_note(turns, ticket),
        "turns": [t.get("turn", "") for t in turns],
    }


def main() -> int:
    if sys.argv[1:]:
        fail(f"usage: {PROG} < turns.json")

    try:
        turns = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        fail(f"stdinのJSONを読み取れません: {e}")

    if not turns:
        print("[]")
        print(f"{PROG}: 入力turnsが0件です", file=sys.stderr)
        return 0

    date_text = turns[0]["timestamp"][:10]
    segments = build_segments(turns)
    records = [
        to_record(date_text, repo, ticket, begin, end, seg_turns)
        for repo, ticket, begin, end, seg_turns in segments
    ]

    print(json.dumps(records, ensure_ascii=False))
    print(f"{PROG}: {date_text} を{len(records)}区間に分割しました({len(turns)}ターン)", file=sys.stderr)
    print(
        "次にすべきこと: 上記JSONを目視チェックし、必要ならticket/noteを修正した上で下流ツールへ渡してください",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
