"""Convert one Codex rollout JSONL transcript to readable Markdown."""
import os
import re
import sys

import codex_session_list

INJECTED_USER_TAGS = re.compile(
    r"<(?:environment_context|skills_instructions|permissions_instructions|"
    r"collaboration_mode|apps_instructions|plugins_instructions)[^>]*>.*?"
    r"</(?:environment_context|skills_instructions|permissions_instructions|"
    r"collaboration_mode|apps_instructions|plugins_instructions)>",
    re.DOTALL,
)


def fail(message):
    print(f"codex_session_to_markdown.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def message_text(payload):
    parts = []
    for block in payload.get("content") or []:
        if not isinstance(block, dict) or block.get("type") not in ("input_text", "output_text"):
            continue
        text = block.get("text", "").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def convert(session):
    messages = []
    for obj in codex_session_list.read_jsonl(session["path"]):
        if obj.get("type") != "response_item":
            continue
        payload = obj.get("payload") or {}
        if payload.get("type") != "message":
            continue
        role = payload.get("role")
        if role not in ("user", "assistant"):
            continue
        text = message_text(payload)
        if role == "user":
            text = INJECTED_USER_TAGS.sub("", text).strip()
        if text:
            messages.append((role, text))

    heading = session["title"] or session["session_id"]
    print(f"# {heading}\n")
    print(f"- Session ID: `{session['session_id']}`")
    if session.get("model"):
        print(f"- Model: `{session['model']}`")
    print()
    for index, (role, text) in enumerate(messages):
        if index:
            print()
        print("## 私：" if role == "user" else "## Codex:")
        print(text)


def resolve_session(arg):
    exact = codex_session_list.find_session_by_id(arg)
    if exact:
        return exact
    try:
        regex = re.compile(arg)
    except re.error as error:
        fail(f"'{arg}' is neither a known session_id nor a valid title regex ({error})")
    candidates = [item for item in codex_session_list.iter_sessions()
                  if item["title"] and regex.search(item["title"])]
    if not candidates:
        fail(f"no session found matching id or title regex: {arg}")
    if len(candidates) > 1:
        listing = "\n".join(f"  {item['session_id']}  {item['title']}" for item in candidates)
        fail(f"title regex matched {len(candidates)} sessions, narrow it down:\n{listing}")
    return candidates[0]


def main():
    if len(sys.argv) != 2:
        fail("expected exactly one argument: <session_id> or <title_regex>")
    convert(resolve_session(sys.argv[1]))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
