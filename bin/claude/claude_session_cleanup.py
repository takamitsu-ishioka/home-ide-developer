"""Implementation for claude_session_cleanup.sh; do not run directly.

Deletes throwaway Claude Code sessions: no title (neither an ai-title nor a
manual /rename custom-title) and at most one exchange. These are almost
always one-off test/programmatic invocations, not real conversations --
see claude_session_list.py for the title/message_count fields this reads.
"""
import os
import sys

import claude_session_list

MAX_MESSAGES = 2  # "at most one exchange" (1 user + 1 assistant message)


def candidates():
    return [
        s
        for s in claude_session_list.iter_sessions()
        if not s["title"] and s["message_count"] <= MAX_MESSAGES
    ]


def print_plan(sessions):
    print(f"{len(sessions)} candidate session(s) (no title, <= {MAX_MESSAGES} messages):", file=sys.stderr)
    for s in sessions:
        print(f"  {s['session_id']}  ({s['message_count']} msg)  {s['path']}", file=sys.stderr)


def fail(message):
    print(f"claude_session_cleanup.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def main():
    dry_run = False
    confirm = False
    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--confirm":
            confirm = True
        else:
            fail(f"unknown option: {arg}")

    sessions = candidates()
    print_plan(sessions)

    if not sessions:
        return

    if dry_run:
        print(f"(dry-run: no sessions deleted; {len(sessions)} would be)", file=sys.stderr)
        return

    if confirm:
        answer = input(f"Delete {len(sessions)} session(s)? [y/N] ")
        if answer.strip().lower() != "y":
            print("Aborted.", file=sys.stderr)
            sys.exit(1)

    for s in sessions:
        os.remove(s["path"])
        print(f"Deleted {s['session_id']}", file=sys.stderr)
    print(f"Done: {len(sessions)} session(s) deleted.", file=sys.stderr)


if __name__ == "__main__":
    main()
