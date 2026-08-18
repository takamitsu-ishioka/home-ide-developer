"""Implementation for claude_session_list.sh; do not run directly.

Single source of truth for Claude Code session discovery/titling, reused
(via `import claude_session_list`) by claude_session_to_markdown.py,
claude_session_cleanup.py, and claude_session_usage_report.py.
"""
import json
import os
import sys
from glob import glob


def iter_sessions():
    """Return every top-level session (excludes subagents/ transcripts),
    newest by mtime first, as dicts with session_id/path/mtime/title/
    message_count."""
    projects_dir = os.path.expanduser("~/.claude/projects")
    jsonl_files = [
        path
        for path in glob(os.path.join(projects_dir, "**", "*.jsonl"), recursive=True)
        if f"{os.sep}subagents{os.sep}" not in path
    ]

    sessions = []
    for path in jsonl_files:
        session_id = os.path.splitext(os.path.basename(path))[0]
        ai_title = ""
        custom_title = ""
        message_count = 0
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    obj_type = obj.get("type")
                    if obj_type == "ai-title":
                        ai_title = obj.get("aiTitle", "")
                    elif obj_type == "custom-title":
                        custom_title = obj.get("customTitle", "")
                    elif obj_type in ("user", "assistant") and not obj.get("isSidechain"):
                        message_count += 1
        except OSError:
            continue
        sessions.append(
            {
                "session_id": session_id,
                "path": path,
                "mtime": os.path.getmtime(path),  # last write to this session file
                # a manual rename (/rename) takes precedence over the AI-generated title
                "title": custom_title or ai_title,
                "message_count": message_count,
            }
        )

    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


def find_session_by_id(session_id):
    for session in iter_sessions():
        if session["session_id"] == session_id:
            return session
    return None


def print_table(sessions, stream=sys.stdout):
    """Human-readable SESSION ID / TITLE table, for tools that still want
    a `--list`-style overview rather than raw tsv/json."""
    col_id = max((len(s["session_id"]) for s in sessions), default=36)
    col_title = max((len(s["title"]) for s in sessions), default=5)
    print(f"{'SESSION ID':<{col_id}}  {'TITLE'}", file=stream)
    print("-" * (col_id + 2 + col_title), file=stream)
    for s in sessions:
        print(f"{s['session_id']:<{col_id}}  {s['title']}", file=stream)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("tsv", "json"):
        print(f"usage: {os.path.basename(sys.argv[0])} <tsv|json>", file=sys.stderr)
        sys.exit(1)

    sessions = iter_sessions()
    if sys.argv[1] == "json":
        print(json.dumps(sessions, ensure_ascii=False))
        return

    for s in sessions:
        print(
            "\t".join(
                [
                    s["session_id"],
                    s["title"],
                    str(s["message_count"]),
                    str(int(s["mtime"])),
                    s["path"],
                ]
            )
        )


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
