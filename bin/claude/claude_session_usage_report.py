"""Implementation for claude_session_usage_report.sh; do not run directly.

Computes cost/duration/token/code-change stats for one Claude Code session
purely from its own transcript (~/.claude/projects/**/<session_id>.jsonl) --
no network calls, no OAuth credentials. This mirrors the "Session" block of
the interactive /status Usage tab, but NOT the "Current session"/"Current
week" rate-limit percentages shown there: those come from Anthropic's
account-usage API (found in the claude binary as /api/oauth/usage), which
needs the OAuth token in ~/.claude/.credentials.json and is deliberately out
of scope here.
"""
import json
import os
import sys
from datetime import datetime, timezone

import claude_session_list

# Pricing per 1M tokens, USD (see ~/.claude/skills/claude-api "Current Models").
# Cache economics have been stable since prompt caching launched: a cache read
# costs ~0.1x base input price; a cache write costs ~1.25x base input (5-minute
# TTL) or ~2x base input (1-hour TTL). web_search_requests are counted but not
# priced -- their $/request rate isn't in the local pricing cache.
SONNET_5_INTRO_CUTOFF = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

PRICING = {
    "claude-fable-5": {"input": 10.00, "output": 50.00},
    "claude-mythos-5": {"input": 10.00, "output": 50.00},
    "claude-opus-5": {"input": 5.00, "output": 25.00},
    "claude-opus-4-8": {"input": 5.00, "output": 25.00},
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def fail(message):
    print(f"claude_session_usage_report.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def model_pricing(model, now):
    if model == "claude-sonnet-5" and now <= SONNET_5_INTRO_CUTOFF:
        return {"input": 2.00, "output": 10.00}  # intro pricing through 2026-08-31
    return PRICING.get(model)


def find_session(session_id):
    session = claude_session_list.find_session_by_id(session_id)
    if not session:
        fail(f"session not found: {session_id}")
    return session


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                yield json.loads(raw_line)
            except json.JSONDecodeError:
                continue  # an active session may have one incomplete final line


def add_code_changes(tool_use_result, totals):
    for hunk in tool_use_result.get("structuredPatch") or []:
        for line in hunk.get("lines", []):
            if line.startswith("+"):
                totals["lines_added"] += 1
            elif line.startswith("-"):
                totals["lines_removed"] += 1
    if tool_use_result.get("type") == "create" and isinstance(tool_use_result.get("content"), str):
        totals["lines_added"] += len(tool_use_result["content"].splitlines())


def add_model_usage(message, by_model):
    usage = message.get("usage")
    model = message.get("model")
    if not usage or not model:
        return
    cache_creation = usage.get("cache_creation") or {}
    total_tokens = (
        usage.get("input_tokens", 0)
        + usage.get("output_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + cache_creation.get("ephemeral_5m_input_tokens", 0)
        + cache_creation.get("ephemeral_1h_input_tokens", 0)
    )
    if total_tokens == 0:
        return  # e.g. model "<synthetic>": Claude Code's internal placeholder turns
    entry = by_model.setdefault(
        model,
        {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_5m_input_tokens": 0,
            "cache_creation_1h_input_tokens": 0,
            "web_search_requests": 0,
        },
    )
    entry["input_tokens"] += usage.get("input_tokens", 0)
    entry["output_tokens"] += usage.get("output_tokens", 0)
    entry["cache_read_input_tokens"] += usage.get("cache_read_input_tokens", 0)
    entry["cache_creation_5m_input_tokens"] += cache_creation.get("ephemeral_5m_input_tokens", 0)
    entry["cache_creation_1h_input_tokens"] += cache_creation.get("ephemeral_1h_input_tokens", 0)
    server_tool_use = usage.get("server_tool_use") or {}
    entry["web_search_requests"] += server_tool_use.get("web_search_requests", 0)


def price_usage(by_model, now):
    total_cost = 0.0
    unpriced_models = []
    for model, entry in by_model.items():
        price = model_pricing(model, now)
        if price is None:
            unpriced_models.append(model)
            entry["cost_usd"] = None
            continue
        cost = (
            entry["input_tokens"] * price["input"]
            + entry["output_tokens"] * price["output"]
            + entry["cache_read_input_tokens"] * price["input"] * 0.1
            + entry["cache_creation_5m_input_tokens"] * price["input"] * 1.25
            + entry["cache_creation_1h_input_tokens"] * price["input"] * 2.0
        ) / 1_000_000
        entry["cost_usd"] = round(cost, 4)
        total_cost += cost
    return round(total_cost, 4), unpriced_models


def collect(session_id):
    session = find_session(session_id)
    now = datetime.now(timezone.utc)

    timestamps = []
    active_ms = 0
    code_totals = {"lines_added": 0, "lines_removed": 0}
    by_model = {}

    for obj in read_jsonl(session["path"]):
        ts = obj.get("timestamp")
        if ts:
            timestamps.append(ts)

        obj_type = obj.get("type")
        if obj_type == "system" and obj.get("subtype") == "turn_duration":
            active_ms += obj.get("durationMs", 0)
        elif obj_type == "user":
            tool_use_result = obj.get("toolUseResult")
            if isinstance(tool_use_result, dict):
                add_code_changes(tool_use_result, code_totals)
        elif obj_type == "assistant":
            add_model_usage(obj.get("message", {}), by_model)

    total_cost_usd, unpriced_models = price_usage(by_model, now)

    # period_start/period_end bound every metric below: cost, token counts,
    # lines_added/removed, and both duration fields are all totals over this
    # same [period_start, period_end] span (the session's first message to
    # its last), not separate or rolling windows.
    period_start = period_end = None
    duration_wall_ms = None
    if timestamps:
        period_start, period_end = min(timestamps), max(timestamps)
        if len(timestamps) >= 2:
            start = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
            end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
            duration_wall_ms = int((end - start).total_seconds() * 1000)

    return {
        "session_id": session_id,
        "title": session["title"],
        "period_start": period_start,
        "period_end": period_end,
        "total_cost_usd": total_cost_usd,
        "unpriced_models": unpriced_models,
        "duration_active_ms": active_ms,
        "duration_wall_ms": duration_wall_ms,
        "lines_added": code_totals["lines_added"],
        "lines_removed": code_totals["lines_removed"],
        "usage_by_model": by_model,
        "note": (
            "Every field above is a total over [period_start, period_end], "
            "i.e. this session's first message to its last -- there is no "
            "separate windowing. duration_wall_ms is real elapsed clock time "
            "across that span (period_end - period_start), including any time "
            "you were away with the session left open. duration_active_ms is "
            "the sum of per-turn active time (model wait + tool execution) "
            "within that same span, so it's normally much smaller than "
            "duration_wall_ms. Computed only from this session's own "
            "transcript (excludes forked/subagent transcripts under "
            "subagents/); web_search_requests are counted but not priced; "
            "does not include the account-wide 5-hour/weekly rate-limit "
            "percentages shown in /status -- those require the live, "
            "OAuth-authenticated usage API (out of scope here)."
        ),
    }


def main():
    if len(sys.argv) != 2:
        fail("expected exactly one argument: <session_id> or --list")

    arg = sys.argv[1]
    if arg == "--list":
        claude_session_list.print_table(claude_session_list.iter_sessions())
        return

    print(json.dumps(collect(arg), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # downstream (e.g. `| head`) stopped reading early; not an error
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
    finally:
        try:
            sys.stdout.close()
        except BrokenPipeError:
            pass  # interpreter-shutdown flush of the (now devnull'd) stdout
