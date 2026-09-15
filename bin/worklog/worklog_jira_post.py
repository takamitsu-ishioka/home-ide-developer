import json
import os
import sys

import worklog_jira_api

PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def print_summary(issue_key: str, started: str, seconds: int, comment: str, email: str) -> None:
    print("入力:", file=sys.stderr)
    print(f"  issue_key         : {issue_key}", file=sys.stderr)
    print(f"  started           : {started}", file=sys.stderr)
    print(f"  time_spent_seconds: {seconds}", file=sys.stderr)
    print(f"  comment           : {comment}", file=sys.stderr)
    print(f"  jira_email        : {email}", file=sys.stderr)
    print(f"  post先            : {worklog_jira_api.JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/worklog", file=sys.stderr)
    print(file=sys.stderr)


def confirm_start() -> bool:
    print("worklogを登録しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
    answer = sys.stdin.readline()
    if not answer:
        print("Cancelled: no input available (non-interactive)", file=sys.stderr)
        return False
    return answer.strip().lower() in ("", "y", "yes")


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    confirm = "--confirm" in args
    positional = [a for a in args if a not in ("--dry-run", "--confirm")]

    if len(positional) != 4:
        fail(f"usage: {PROG} <issue_key> <started> <time_spent_seconds> <comment> [--dry-run] [--confirm]")
    issue_key, started_text, seconds_text, comment = positional
    try:
        seconds = int(seconds_text)
    except ValueError:
        fail(f"invalid time_spent_seconds: {seconds_text}")
    if seconds < 60:
        fail(f"time_spent_seconds must be >= 60 (Jira worklogの最小単位): {seconds}")

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    try:
        started = worklog_jira_api.resolve_started(started_text)
    except worklog_jira_api.JiraApiError as e:
        fail(str(e))
    print_summary(issue_key, started, seconds, comment, email)

    body = {"comment": comment, "started": started, "timeSpentSeconds": seconds}

    if dry_run:
        print("[dry-run] would POST:", file=sys.stderr)
        print(json.dumps(body, ensure_ascii=False, indent=2), file=sys.stderr)
        print(json.dumps({"dry_run": True, **body}, ensure_ascii=False))
        return 0

    if confirm and not confirm_start():
        print("Cancelled.", file=sys.stderr)
        return 1

    try:
        result = worklog_jira_api.post_worklog(issue_key, started, seconds, comment, email, token)
    except worklog_jira_api.JiraApiError as e:
        fail(str(e))
    print(f"worklogを登録しました: {issue_key} ({seconds}秒)", file=sys.stderr)
    print(f"次にすべきこと: Jiraダッシュボード10011を開き、Timesheetガジェットに今回の分が反映されているか確認してください", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
