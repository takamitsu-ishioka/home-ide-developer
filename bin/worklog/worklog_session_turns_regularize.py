import json
import os
import sys
from datetime import datetime, timedelta

import worklog_jira_api

PROG = os.path.basename(__file__)
DEFAULT_TICKET = "GENERAL-451"  # worklog_session_turns_list.pyのcwd解決の既定値
NONDETERMINISTIC_TICKET = "_nondeterministic_"  # 論理的手がかりの無いturn用の特殊ticket
GAP_TICKET = "_gap_"  # turn間の空白期間用の特殊ticket


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def ticket_url(ticket: str) -> str:
    return f"{worklog_jira_api.JIRA_BASE_URL}/browse/{ticket}"


def mark_nondeterministic(turns: list[dict]) -> int:
    """cwd解決できなかった(ticket==DEFAULT_TICKET)turnをNONDETERMINISTIC_TICKETへ書き換える。"""
    count = 0
    for turn in turns:
        if turn.get("ticket") == DEFAULT_TICKET:
            turn["ticket"] = NONDETERMINISTIC_TICKET
            turn["ticket_url"] = ticket_url(NONDETERMINISTIC_TICKET)
            count += 1
    return count


def turn_start(turn: dict) -> datetime:
    """そのturn自身の処理開始時刻(完了時刻 - 処理時間)。"""
    completion = datetime.fromisoformat(turn["timestamp"])
    return completion - timedelta(milliseconds=turn.get("duration_ms", 0))


def gap_markers(prev_turn: dict, next_turn: dict) -> list[dict]:
    """prev_turnとnext_turnがセッションを跨いでおり(session_idが異なる)、かつ実際の空白が
    あれば、境界を正確に表す2つのマーカーturnを返す(無ければ空リスト)。

    gapは「turn N, claude exit, <elapse>, claude start, turn N+1」の<elapse>を指す
    (同一セッション内の応答テンポの間隔はgapではない)。

    1つ目: prev_turnの完了時刻に"_gap_"を置き、prev_turnの区間をそこで正しく閉じる。
    2つ目: next_turnの処理開始時刻にnext_turnと同じrepo/ticketを置き、"_gap_"区間を
    正確なgapサイズ(next_turnの処理開始時刻 - prev_turnの完了時刻)で閉じる。next_turn
    本体と同じ(repo,ticket)なので、worklog_session_infer.pyのセグメント化でnext_turn
    自身とそのままマージされる。
    """
    if prev_turn.get("session_id") == next_turn.get("session_id"):
        return []

    prev_completion = datetime.fromisoformat(prev_turn["timestamp"])
    next_start = turn_start(next_turn)
    if (next_start - prev_completion).total_seconds() <= 0:
        return []

    gap_start_marker = {
        "turn": "",
        "timestamp": prev_turn["timestamp"],
        "duration_ms": 0,
        "session_id": prev_turn.get("session_id", ""),
        "cwd": "",
        "repo": "none",
        "ticket": GAP_TICKET,
        "ticket_url": ticket_url(GAP_TICKET),
        "user": [],
        "agent": [],
    }
    gap_end_marker = {
        "turn": "",
        "timestamp": next_start.isoformat(timespec="seconds"),
        "duration_ms": 0,
        "session_id": next_turn.get("session_id", ""),
        "cwd": next_turn.get("cwd", ""),
        "repo": next_turn.get("repo", "none"),
        "ticket": next_turn.get("ticket", DEFAULT_TICKET),
        "ticket_url": next_turn.get("ticket_url", ""),
        "user": [],
        "agent": [],
    }
    return [gap_start_marker, gap_end_marker]


def insert_gaps(turns: list[dict]) -> list[dict]:
    if not turns:
        return turns
    result = [turns[0]]
    for prev_turn, next_turn in zip(turns, turns[1:]):
        result.extend(gap_markers(prev_turn, next_turn))
        result.append(next_turn)
    return result


def main() -> int:
    if sys.argv[1:]:
        fail(f"usage: {PROG} < turns.json")

    try:
        turns = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        fail(f"stdinのJSONを読み取れません: {e}")

    nondeterministic_count = mark_nondeterministic(turns)
    regularized = insert_gaps(turns)
    gap_count = (len(regularized) - len(turns)) // 2

    print(json.dumps(regularized, ensure_ascii=False))
    print(
        f"{PROG}: {len(turns)}ターン中{nondeterministic_count}件を{NONDETERMINISTIC_TICKET}へ、"
        f"{gap_count}箇所に{GAP_TICKET}を挿入しました",
        file=sys.stderr,
    )
    print(
        f"次にすべきこと: {NONDETERMINISTIC_TICKET}・{GAP_TICKET}を解決するルールを"
        "ticket_guess_rulesに追加するか、下流で人間が直接ticketを書き換えてください",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
