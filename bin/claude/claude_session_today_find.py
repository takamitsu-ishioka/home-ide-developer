"""Implementation for claude_session_today_find.sh; do not run directly.

Find today's (local date) Claude Code session for a given directory, by
matching the 'cwd' recorded inside each session log (via claude_session_list,
the shared session-discovery module) - not by guessing the
~/.claude/projects/<encoded-path>/ directory-name encoding, which is
unofficial and unreliable. subagents/ (forked-agent transcripts) are
excluded by claude_session_list. With no format given, prints the session id
to stdout (or nothing if none is found) - this is the mode claude_launch.sh
relies on. With tsv|json given, prints the full record instead, using
claude_session_list's to_record()/RECORD_FIELDS (title first, plus ctime
and an ISO-localtime mtime).
"""
import json
import os
import sys
from datetime import datetime

import claude_session_list

PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def print_record(record: dict, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(record, ensure_ascii=False))
    else:
        print("\t".join(str(record[field]) for field in claude_session_list.RECORD_FIELDS))


def main() -> int:
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] not in ("tsv", "json")):
        fail(f"usage: {PROG} <dir> [tsv|json]")

    target_dir = os.path.abspath(sys.argv[1])
    fmt = sys.argv[2] if len(sys.argv) == 3 else None
    today = datetime.now().date()

    candidates = [
        s
        for s in claude_session_list.iter_sessions()
        if s["cwd"] == target_dir and datetime.fromtimestamp(s["mtime"]).date() == today
    ]

    if not candidates:
        return 0

    best = candidates[0]  # iter_sessions() is already newest-mtime-first

    if len(candidates) > 1:
        print(
            f"{PROG}: {len(candidates)} sessions found for today in {target_dir}, "
            f"picking the most recently updated one ({best['session_id']}):",
            file=sys.stderr,
        )
        for s in candidates:
            print(f"  {s['session_id']}  mtime={datetime.fromtimestamp(s['mtime']).isoformat()}", file=sys.stderr)

    if fmt:
        print_record(claude_session_list.to_record(best), fmt)
    else:
        print(best["session_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
