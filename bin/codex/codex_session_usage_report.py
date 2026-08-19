"""Compute locally available duration and token statistics for a Codex session."""
import json
import os
import sys
from datetime import datetime

import codex_session_list


def fail(message):
    print(f"codex_session_usage_report.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def collect(session_id):
    session = codex_session_list.find_session_by_id(session_id)
    if not session:
        fail(f"session not found: {session_id}")
    timestamps = []
    active_ms = 0
    usage = {}
    for obj in codex_session_list.read_jsonl(session["path"]):
        timestamp = obj.get("timestamp")
        if timestamp:
            timestamps.append(timestamp)
        payload = obj.get("payload") or {}
        if obj.get("type") == "event_msg" and payload.get("type") == "task_complete":
            active_ms += payload.get("duration_ms") or 0
        if obj.get("type") == "event_msg" and payload.get("type") == "token_count":
            current = (payload.get("info") or {}).get("total_token_usage")
            if isinstance(current, dict):
                usage = current
    period_start = min(timestamps) if timestamps else None
    period_end = max(timestamps) if timestamps else None
    wall_ms = None
    if period_start and period_end:
        wall_ms = int((parse_time(period_end) - parse_time(period_start)).total_seconds() * 1000)
    return {
        "session_id": session_id,
        "title": session["title"],
        "model": session.get("model"),
        "period_start": period_start,
        "period_end": period_end,
        "duration_active_ms": active_ms,
        "duration_wall_ms": wall_ms,
        "token_usage": usage,
        "total_cost_usd": None,
        "note": (
            "Token counts are the last cumulative total_token_usage event in the local rollout. "
            "duration_active_ms sums completed Codex task durations; duration_wall_ms is elapsed "
            "clock time. Cost is not derived because local subscription sessions do not expose "
            "a reliable billed price."
        ),
    }


def main():
    if len(sys.argv) != 2:
        fail("expected exactly one argument: <session_id> or --list")
    if sys.argv[1] == "--list":
        codex_session_list.print_table(codex_session_list.iter_sessions())
        return
    print(json.dumps(collect(sys.argv[1]), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
