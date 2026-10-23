"""Implementation for claude_session_list.sh; do not run directly.

Single source of truth for Claude Code session discovery/titling, reused
(via `import claude_session_list`) by claude_session_to_markdown.py,
claude_session_cleanup.py, claude_session_today_find.py, and
claude_session_resolve.py (used by claude_launch.sh). Also the single
source of truth for the display record shape (title first, ctime added,
mtime as ISO-localtime) via to_record()/RECORD_FIELDS, reused by this
script's own json output and by claude_session_today_find.py's tsv/json
output.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from glob import glob


class SessionResolutionError(Exception):
    """Raised by resolve_session() when arg matches none or more than one session."""


def iter_sessions():
    """Return every top-level session (excludes subagents/ transcripts),
    newest by mtime first, as dicts with session_id/path/mtime/title/
    message_count/cwd."""
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
        cwd = None
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if cwd is None and obj.get("cwd"):
                        cwd = obj["cwd"]
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
                "cwd": cwd,
            }
        )

    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


def find_session_by_id(session_id):
    for session in iter_sessions():
        if session["session_id"] == session_id:
            return session
    return None


def resolve_session(arg):
    """Resolve arg to a single session dict: tries an exact session_id match
    first, then falls back to a regex matched against session titles. Raises
    SessionResolutionError if arg matches no session or more than one."""
    exact = find_session_by_id(arg)
    if exact:
        return exact

    try:
        regex = re.compile(arg)
    except re.error as e:
        raise SessionResolutionError(f"'{arg}' is neither a known session_id nor a valid title regex ({e})")

    candidates = [s for s in iter_sessions() if s["title"] and regex.search(s["title"])]
    if not candidates:
        raise SessionResolutionError(f"no session found matching id or title regex: {arg}")
    if len(candidates) > 1:
        listing = "\n".join(f"  {c['session_id']}  {c['title']}" for c in candidates)
        raise SessionResolutionError(f"title regex matched {len(candidates)} sessions, narrow it down:\n{listing}")
    return candidates[0]


RECORD_FIELDS = ("title", "session_id", "path", "ctime", "mtime", "message_count", "cwd")


def to_iso_localtime(epoch):
    """Convert a Unix epoch (float) to an ISO 8601 string in local time."""
    return datetime.fromtimestamp(epoch).astimezone().isoformat()


def get_birthtime(path):
    """Return the file's true creation time (Unix epoch, float).

    os.path.getctime()/os.stat().st_ctime is the inode's metadata-change
    time, not creation time - on Linux it advances on every write, so for
    an append-only session log it ends up equal to mtime. The kernel/
    filesystem here does track true birth time (`stat` shows a `Birth:`
    line), but Python's os.stat() doesn't expose it on Linux, so shell out
    to `stat -c %W`. Falls back to ctime if the filesystem doesn't support
    birth time (%W prints 0 in that case).
    """
    birthtime = int(subprocess.run(["stat", "-c", "%W", path], capture_output=True, text=True, check=True).stdout)
    return float(birthtime) if birthtime > 0 else os.path.getctime(path)


def to_record(session):
    """Reshape an iter_sessions() dict into the display record used by this
    script's json output and by claude_session_today_find.py: title first,
    ctime added (true file creation time, not tracked by iter_sessions),
    and ctime/mtime both rendered as ISO-localtime instead of a raw
    epoch."""
    return {
        "title": session["title"],
        "session_id": session["session_id"],
        "path": session["path"],
        "ctime": to_iso_localtime(get_birthtime(session["path"])),
        "mtime": to_iso_localtime(session["mtime"]),
        "message_count": session["message_count"],
        "cwd": session["cwd"],
    }


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
        print(json.dumps([to_record(s) for s in sessions], ensure_ascii=False))
        return

    for s in sessions:
        print(
            "\t".join(
                [
                    s["session_id"],
                    s["title"],
                    str(s["message_count"]),
                    str(int(s["mtime"])),
                    s["cwd"] or "",
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
