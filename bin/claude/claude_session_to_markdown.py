"""Implementation for claude_session_to_markdown.sh; do not run directly.

Converts one Claude Code session to Markdown. The argument is resolved as
an exact session_id first; if that doesn't match, it's tried as a regex
against session titles (see claude_session_list.py).
"""
import json
import os
import re
import sys

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
                messages.append((t, text))

    out = []
    for role, text in messages:
        heading = "## 私：" if role == "user" else "## Claude:"
        out.append(f"{heading}\n{text}")

    print("\n\n".join(out))


def resolve_session_path(arg):
    exact = claude_session_list.find_session_by_id(arg)
    if exact:
        return exact["path"]

    try:
        regex = re.compile(arg)
    except re.error as e:
        fail(f"'{arg}' is neither a known session_id nor a valid title regex ({e})")

    candidates = [
        s for s in claude_session_list.iter_sessions() if s["title"] and regex.search(s["title"])
    ]
    if not candidates:
        fail(f"no session found matching id or title regex: {arg}")
    if len(candidates) > 1:
        listing = "\n".join(f"  {c['session_id']}  {c['title']}" for c in candidates)
        fail(f"title regex matched {len(candidates)} sessions, narrow it down:\n{listing}")
    return candidates[0]["path"]


def main():
    if len(sys.argv) != 2:
        fail("expected exactly one argument: <session_id> or <title_regex>")
    convert(resolve_session_path(sys.argv[1]))


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
