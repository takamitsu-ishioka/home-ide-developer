"""Implementation for codex_session_resolve.sh; do not run directly.

Resolves an argument (exact session_id, or a regex matched against session
titles) to a single session_id and prints it to stdout. Thin CLI over
codex_session_list.resolve_session(), used by codex_launch.sh to let a
user jump straight into an existing session by id or title.
"""
import sys

import codex_session_list


def fail(message):
    print(f"codex_session_resolve.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def main():
    if len(sys.argv) != 2:
        fail("expected exactly one argument: <session_id> or <title_regex>")
    try:
        session = codex_session_list.resolve_session(sys.argv[1])
    except codex_session_list.SessionResolutionError as e:
        fail(str(e))
    print(session["session_id"])


if __name__ == "__main__":
    main()
