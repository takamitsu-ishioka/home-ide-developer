"""Implementation for agent_session_to_markdown.sh; do not run directly."""

import json
import os
import sys
from glob import glob
from pathlib import Path

sys.path.insert(0, str(Path.home() / "bin" / "claude"))
import claude_session_list  # noqa: E402
import claude_session_to_markdown  # noqa: E402


CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"
TITLE_LIMIT = 80


def fail(message):
    print(f"agent_session_to_markdown.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # An active Codex session may have one incomplete final line.
                continue


def codex_session_id(path):
    for obj in read_jsonl(path):
        if obj.get("type") != "session_meta":
            continue
        payload = obj.get("payload", {})
        return payload.get("session_id") or payload.get("id") or ""
    return ""


def codex_title(path):
    for obj in read_jsonl(path):
        if obj.get("type") != "event_msg":
            continue
        payload = obj.get("payload", {})
        if payload.get("type") != "user_message":
            continue
        title = " ".join(payload.get("message", "").split())
        if len(title) > TITLE_LIMIT:
            return title[: TITLE_LIMIT - 1] + "…"
        return title
    return ""


def codex_session_files():
    pattern = str(CODEX_SESSIONS_DIR / "**" / "*.jsonl")
    return [Path(path) for path in glob(pattern, recursive=True)]


def list_codex_sessions():
    sessions = []
    for path in codex_session_files():
        session_id = codex_session_id(path)
        if session_id:
            sessions.append((path.stat().st_mtime, session_id, codex_title(path)))

    sessions.sort(reverse=True)
    column_width = max((len(session[1]) for session in sessions), default=36)
    title_width = max((len(session[2]) for session in sessions), default=5)
    print(f"{'SESSION ID':<{column_width}}  TITLE")
    print("-" * (column_width + 2 + title_width))
    for _, session_id, title in sessions:
        print(f"{session_id:<{column_width}}  {title}")


def find_codex_session(session_id):
    matches = []
    for path in codex_session_files():
        if codex_session_id(path) == session_id:
            matches.append(path)

    if not matches:
        fail(f"Codex session not found: {session_id}")
    if len(matches) > 1:
        fail(f"Multiple Codex sessions found for ID: {session_id}")
    return matches[0]


def convert_codex_session(path):
    messages = []
    for obj in read_jsonl(path):
        if obj.get("type") != "event_msg":
            continue
        payload = obj.get("payload", {})
        event_type = payload.get("type")
        if event_type == "user_message":
            role = "user"
        elif event_type == "agent_message":
            role = "assistant"
        else:
            continue

        text = payload.get("message", "").strip()
        if text:
            messages.append((role, text))

    sections = []
    for role, text in messages:
        heading = "## 私：" if role == "user" else "## Codex:"
        sections.append(f"{heading}\n{text}")
    print("\n\n".join(sections))


def main():
    if len(sys.argv) != 3:
        fail("expected agent name and session ID or --list")

    agent_name, operation = sys.argv[1:]
    if agent_name == "claude":
        if operation == "--list":
            claude_session_list.print_table(claude_session_list.iter_sessions())
        else:
            claude_session_to_markdown.convert(
                claude_session_to_markdown.resolve_session_path(operation)
            )
        return

    if agent_name == "codex":
        if operation == "--list":
            list_codex_sessions()
        else:
            convert_codex_session(find_codex_session(operation))
        return

    fail(f"unknown agent: {agent_name}")


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
