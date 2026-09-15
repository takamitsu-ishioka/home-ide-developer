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


def print_summary(issue_key: str, worklog_id: str, email: str) -> None:
    print("入力:", file=sys.stderr)
    print(f"  issue_key  : {issue_key}", file=sys.stderr)
    print(f"  worklog_id : {worklog_id}", file=sys.stderr)
    print(f"  jira_email : {email}", file=sys.stderr)
    print(
        f"  削除対象  : {worklog_jira_api.JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/worklog/{worklog_id}",
        file=sys.stderr,
    )
    print(file=sys.stderr)


def confirm_start() -> bool:
    print("このworklogを削除しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
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

    if len(positional) != 2:
        fail(f"usage: {PROG} <issue_key> <worklog_id> [--dry-run] [--confirm]")
    issue_key, worklog_id = positional

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    print_summary(issue_key, worklog_id, email)

    if dry_run:
        print("[dry-run] would DELETE the worklog above", file=sys.stderr)
        return 0

    if confirm and not confirm_start():
        print("Cancelled.", file=sys.stderr)
        return 1

    try:
        worklog_jira_api.delete_worklog(issue_key, worklog_id, email, token)
    except worklog_jira_api.JiraApiError as e:
        fail(str(e))
    print(f"worklogを削除しました: {issue_key} (id={worklog_id})", file=sys.stderr)
    print("次にすべきこと: 必要な代替worklogをworklog_jira_post.shで登録してください", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
