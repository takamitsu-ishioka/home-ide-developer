"""Shared Codex session discovery used by the codex_session_* scripts."""
import json
import os
import sqlite3
import sys
from glob import glob


def read_jsonl(path):
    try:
        with open(path, encoding="utf-8") as stream:
            for raw_line in stream:
                try:
                    yield json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def message_role(obj):
    if obj.get("type") != "response_item":
        return None
    payload = obj.get("payload") or {}
    if payload.get("type") != "message":
        return None
    return payload.get("role") if payload.get("role") in ("user", "assistant") else None


def state_rows():
    path = os.path.expanduser("~/.codex/state_5.sqlite")
    if not os.path.isfile(path):
        return {}
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, rollout_path, title, name, updated_at, updated_at_ms, "
            "archived, model, source FROM threads"
        )
        return {row["id"]: dict(row) for row in rows}
    except (OSError, sqlite3.Error):
        return {}


def metadata(path):
    session_id = ""
    timestamp = None
    for obj in read_jsonl(path):
        if obj.get("type") == "session_meta":
            payload = obj.get("payload") or {}
            session_id = payload.get("id") or payload.get("session_id") or ""
            timestamp = payload.get("timestamp")
            break
    return session_id, timestamp


def iter_sessions():
    sessions_dir = os.path.expanduser("~/.codex/sessions")
    paths = glob(os.path.join(sessions_dir, "**", "*.jsonl"), recursive=True)
    rows = state_rows()
    sessions = []
    for path in paths:
        session_id, _ = metadata(path)
        if not session_id:
            session_id = os.path.splitext(os.path.basename(path))[0].rsplit("-", 5)[-1]
        row = rows.get(session_id, {})
        counts = {"user": 0, "assistant": 0}
        for obj in read_jsonl(path):
            role = message_role(obj)
            if role:
                counts[role] += 1
        mtime = os.path.getmtime(path)
        updated_ms = row.get("updated_at_ms") or 0
        if updated_ms:
            mtime = updated_ms / 1000
        sessions.append(
            {
                "session_id": session_id,
                "title": row.get("name") or row.get("title") or "",
                "message_count": counts["user"] + counts["assistant"],
                "user_message_count": counts["user"],
                "assistant_message_count": counts["assistant"],
                "mtime": mtime,
                "path": path,
                "archived": bool(row.get("archived", False)),
                "model": row.get("model"),
                "source": row.get("source"),
            }
        )
    sessions.sort(key=lambda session: session["mtime"], reverse=True)
    return sessions


def find_session_by_id(session_id):
    return next((session for session in iter_sessions() if session["session_id"] == session_id), None)


def print_table(sessions, stream=sys.stdout):
    col_id = max((len(item["session_id"]) for item in sessions), default=36)
    print(f"{'SESSION ID':<{col_id}}  TITLE", file=stream)
    print("-" * (col_id + 7), file=stream)
    for item in sessions:
        print(f"{item['session_id']:<{col_id}}  {item['title']}", file=stream)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("tsv", "json"):
        print(f"usage: {os.path.basename(sys.argv[0])} <tsv|json>", file=sys.stderr)
        raise SystemExit(1)
    sessions = iter_sessions()
    if sys.argv[1] == "json":
        print(json.dumps(sessions, ensure_ascii=False))
        return
    for item in sessions:
        print("\t".join((
            item["session_id"], item["title"], str(item["message_count"]),
            str(int(item["mtime"])), item["path"],
        )))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
