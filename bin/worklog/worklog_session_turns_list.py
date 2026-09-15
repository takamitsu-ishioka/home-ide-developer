import glob
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta

import worklog_jira_api

PROG = os.path.basename(__file__)
SYSTEM_REMINDER_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
INTEGRATED_WORK_ENVIRONMENT_DIR = os.path.expanduser("~/bin/integrated_work_environment")
PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
DEFAULT_TICKET = "GENERAL-451"  # cwd => ticket が解決できない場合等の受け皿(その他の雑多な作業)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def resolve_repo_ticket(cwd: str, cache: dict[str, tuple[str, str]]) -> tuple[str, str]:
    """(repo表示名, ticket_key)を返す。解決できなければ("none", DEFAULT_TICKET)。"""
    if cwd in cache:
        return cache[cwd]

    result = run([os.path.join(INTEGRATED_WORK_ENVIRONMENT_DIR, "repo_issue_from_cwd.sh"), cwd])
    if result.returncode != 0:
        cache[cwd] = ("none", DEFAULT_TICKET)
        return cache[cwd]
    repo, issue_number = result.stdout.strip().split("\t")
    repo_label = repo.split("/")[-1]

    result = run([os.path.join(INTEGRATED_WORK_ENVIRONMENT_DIR, "ticket_from_issue.sh"), repo, issue_number])
    ticket = result.stdout.strip() if result.returncode == 0 else DEFAULT_TICKET
    cache[cwd] = (repo_label, ticket)
    return cache[cwd]


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def resolve_target_date(date_text: str) -> date:
    try:
        return date.fromisoformat(date_text)
    except ValueError:
        fail(f"invalid date: {date_text} (expected YYYY-MM-DD)")


def resolve_limit(text: str) -> int | None:
    if text == "none":
        return None
    try:
        limit = int(text)
    except ValueError:
        fail(f"invalid limit: {text!r} (expected a non-negative integer or 'none')")
    if limit < 0:
        fail(f"invalid limit: {text!r} (expected a non-negative integer or 'none')")
    return limit


def truncate(text: str, limit: int | None) -> str:
    if limit is None or len(text) <= limit:
        return text
    remainder = len(text) - limit
    return f"{text[:limit]}...(他{remainder}文字)"


def clean_user_text(text: str) -> str:
    """system-reminderなど、人間が実際に打ったのではない注入テキストを取り除く。"""
    return SYSTEM_REMINDER_RE.sub("", text).strip()


def append_lines(target: list[str], text: str, limit: int | None, prefix: str = "") -> None:
    """textを(先にtruncateしてから)改行で分割し、1行ずつ別要素としてtargetへ追加する。

    prefixを指定した場合、先頭行にのみ付与する("calling subagent for ..."等の接頭辞用)。
    """
    lines = truncate(text, limit).split("\n")
    target.append(prefix + lines[0])
    target.extend(lines[1:])


def extract_result_text(content) -> str:
    """tool_resultのcontent(文字列、または[{"type":"text",...}]のリスト)からテキストのみを結合する。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "".join(parts)
    return ""


def process_file(
    path: str, day_start: datetime, day_end: datetime, limit: int | None, ticket_cache: dict
) -> list[dict]:
    """1つのセッションログを先頭から走査し、turn_duration境界ごとにuser/agentの発言を束ねる。

    トップレベルagentがAgentツール(サブエージェント/fork)を呼んだ場合、対話内容そのものは
    含めず、「呼んだ」「回答が来た」という事実だけをagent配列へ記録する。
    """
    turns: list[dict] = []
    current_user: list[str] = []
    current_agent: list[str] = []
    pending_agent_calls: dict[str, str] = {}  # tool_use_id -> description

    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return turns

    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        obj_type = obj.get("type")

        if obj_type == "system" and obj.get("subtype") == "turn_duration":
            ts = obj.get("timestamp")
            cwd = obj.get("cwd")
            if ts and cwd:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
                if day_start <= dt < day_end:
                    repo, ticket = resolve_repo_ticket(cwd, ticket_cache)
                    turns.append(
                        {
                            "turn": obj.get("uuid", ""),
                            "timestamp": dt.isoformat(timespec="seconds"),
                            "duration_ms": obj.get("durationMs", 0),
                            "session_id": obj.get("sessionId", ""),
                            "cwd": cwd,
                            "repo": repo,
                            "ticket": ticket,
                            "ticket_url": f"{worklog_jira_api.JIRA_BASE_URL}/browse/{ticket}",
                            "user": current_user,
                            "agent": current_agent,
                        }
                    )
            current_user = []
            current_agent = []
            continue

        if obj_type == "user":
            content = obj.get("message", {}).get("content")
            if isinstance(content, str):
                text = clean_user_text(content)
                if text:
                    append_lines(current_user, text, limit)
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        text = clean_user_text(block.get("text", ""))
                        if text:
                            append_lines(current_user, text, limit)
                    elif btype == "tool_result":
                        tool_use_id = block.get("tool_use_id")
                        if tool_use_id in pending_agent_calls:
                            pending_agent_calls.pop(tool_use_id)
                            result_text = extract_result_text(block.get("content"))
                            append_lines(current_agent, result_text, limit, prefix="回答が来ました。")
                    # type=="image"などは無視する(画像は不要)
            continue

        if obj_type == "assistant":
            content = obj.get("message", {}).get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        text = block.get("text", "").strip()
                        if text:
                            append_lines(current_agent, text, limit)
                    elif btype == "tool_use" and block.get("name") == "Agent":
                        tool_use_id = block.get("id")
                        description = block.get("input", {}).get("description", "")
                        if tool_use_id:
                            pending_agent_calls[tool_use_id] = description
                        append_lines(current_agent, description, limit, prefix="calling subagent for ")
                    # thinkingや他のtool_useは"ユーザーへの発言"ではないため含めない
            continue

    return turns


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 2:
        fail(f"usage: {PROG} <date> <limit>")
    target_date = resolve_target_date(args[0])
    limit = resolve_limit(args[1])

    day_start = datetime.combine(target_date, datetime.min.time()).astimezone()
    day_end = day_start + timedelta(days=1)

    jsonl_files = [
        path
        for path in glob.glob(os.path.join(PROJECTS_DIR, "**", "*.jsonl"), recursive=True)
        if f"{os.sep}subagents{os.sep}" not in path
    ]

    ticket_cache: dict[str, tuple[str, str]] = {}
    all_turns: list[dict] = []
    for path in jsonl_files:
        all_turns.extend(process_file(path, day_start, day_end, limit, ticket_cache))

    all_turns.sort(key=lambda t: t["timestamp"])

    print(json.dumps(all_turns, ensure_ascii=False))
    print(f"{PROG}: {target_date.isoformat()}: {len(all_turns)}ターン", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
