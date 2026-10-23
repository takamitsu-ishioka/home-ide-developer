"""Implementation for claude_session_to_markdown.sh; do not run directly.

Converts one Claude Code session to Markdown. The argument is resolved as
an exact session_id first; if that doesn't match, it's tried as a regex
against session titles (see claude_session_list.py).
"""
import json
import os
import re
import sys
from datetime import datetime

import claude_session_list

SYSTEM_TAG_PATTERN = re.compile(
    r"<(?:ide_selection|ide_opened_file|system-reminder|command-name)[^>]*>.*?</(?:ide_selection|ide_opened_file|system-reminder|command-name)>",
    re.DOTALL,
)


def fail(message):
    print(f"claude_session_to_markdown.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def extract_user_text(content):
    parts = []
    for block in content:
        if block.get("type") != "text":
            continue
        text = SYSTEM_TAG_PATTERN.sub("", block.get("text", ""))
        text = text.strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def extract_assistant_text(content):
    parts = []
    for block in content:
        if block.get("type") != "text":
            continue
        text = block.get("text", "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def format_local_timestamp(iso_timestamp):
    return datetime.fromisoformat(iso_timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def convert(jsonl_path):
    messages = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("isSidechain"):
                continue
            t = obj.get("type")
            if t not in ("user", "assistant"):
                continue
            content = obj.get("message", {}).get("content", [])
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            if t == "user":
                text = extract_user_text(content)
            else:
                text = extract_assistant_text(content)
            if text:
                messages.append((t, text, obj.get("timestamp")))

    out = []
    for role, text, timestamp in messages:
        heading = "## 私：" if role == "user" else "## Claude:"
        if timestamp:
            heading = f"{heading} {format_local_timestamp(timestamp)}"
        out.append(f"{heading}\n{text}")

    print("\n\n".join(out))


def main():
    if len(sys.argv) != 2:
        fail("expected exactly one argument: <session_id> or <title_regex>")
    try:
        session = claude_session_list.resolve_session(sys.argv[1])
    except claude_session_list.SessionResolutionError as e:
        fail(str(e))
    convert(session["path"])


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
