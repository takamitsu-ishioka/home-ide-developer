"""Conservatively delete untitled, one-turn Codex sessions via `codex delete`."""
import subprocess
import sys

import codex_session_list


def fail(message):
    print(f"codex_session_cleanup.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def candidates():
    return [item for item in codex_session_list.iter_sessions()
            if not item["title"] and item["user_message_count"] <= 1]


def main():
    dry_run = "--dry-run" in sys.argv[1:]
    confirm = "--confirm" in sys.argv[1:]
    unknown = [arg for arg in sys.argv[1:] if arg not in ("--dry-run", "--confirm")]
    if unknown:
        fail(f"unknown option: {unknown[0]}")
    sessions = candidates()
    print(f"{len(sessions)} candidate session(s) (no title, <= 1 user message):", file=sys.stderr)
    for item in sessions:
        print(f"  {item['session_id']}  ({item['message_count']} msg)  {item['path']}", file=sys.stderr)
    if not sessions or dry_run:
        if dry_run:
            print(f"(dry-run: no sessions deleted; {len(sessions)} would be)", file=sys.stderr)
        return
    if confirm and input(f"Delete {len(sessions)} session(s)? [y/N] ").strip().lower() != "y":
        print("Aborted.", file=sys.stderr)
        raise SystemExit(1)
    for item in sessions:
        subprocess.run(["codex", "delete", item["session_id"]], check=True)
        print(f"Deleted {item['session_id']}", file=sys.stderr)
    print(f"Done: {len(sessions)} session(s) deleted.", file=sys.stderr)


if __name__ == "__main__":
    main()
