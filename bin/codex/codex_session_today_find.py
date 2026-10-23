"""Implementation for codex_session_today_find.sh; do not run directly.

Find today's (local date) Codex session for a given directory, by matching
the 'cwd' recorded in each session's session_meta (via codex_session_list,
the shared session-discovery module). Prints the session id to stdout (or
nothing if none is found) - this is the mode codex_launch.sh relies on.
"""
import os
import sys
from datetime import datetime

import codex_session_list

PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if len(sys.argv) != 2:
        fail(f"usage: {PROG} <dir>")

    target_dir = os.path.abspath(sys.argv[1])
    today = datetime.now().date()

    candidates = [
        s
        for s in codex_session_list.iter_sessions()
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

    print(best["session_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
