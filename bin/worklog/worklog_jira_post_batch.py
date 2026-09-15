import json
import os
import sys
from datetime import datetime

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


def seconds_between(date_text: str, start_hm: str, end_hm: str) -> int:
    start = datetime.strptime(f"{date_text} {start_hm}", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{date_text} {end_hm}", "%Y-%m-%d %H:%M")
    return int((end - start).total_seconds())


def confirm_start(count: int) -> bool:
    print(f"{count}件をJiraへ一括登録しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
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
    if len(positional) != 1:
        fail(f"usage: {PROG} <file> [--dry-run] [--confirm]")
    file_path = positional[0]

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    try:
        with open(file_path, encoding="utf-8") as f:
            segments = json.load(f)
    except OSError as e:
        fail(f"{file_path}を読み取れません: {e}")
    except json.JSONDecodeError as e:
        fail(f"{file_path}のJSONを読み取れません: {e}")

    targets = [s for s in segments if not s.get("posted_at")]

    print("入力:", file=sys.stderr)
    print(f"  対象     : {file_path}", file=sys.stderr)
    print(f"  未投稿件数: {len(targets)}件", file=sys.stderr)
    print(file=sys.stderr)
    if not targets:
        print(f"{PROG}: 未投稿の要素がありません", file=sys.stderr)
        return 0

    plan = []
    for seg in targets:
        seconds = seconds_between(seg["date"], seg["start"], seg["end"])
        if seconds < 60:
            print(
                f"{PROG}: 警告: {seg['date']} {seg['start']}-{seg['end']} {seg['ticket']} は"
                f"{seconds}秒でJira worklogの最小単位(60秒)未満のためスキップします",
                file=sys.stderr,
            )
            continue
        started = worklog_jira_api.resolve_started(f"{seg['date']}T{seg['start']}")
        plan.append((seg, started, seconds))
        print(f"  {seg['date']} {seg['start']}-{seg['end']} ({seg['duration']}) {seg['ticket']} {seg['note']}", file=sys.stderr)
    print(file=sys.stderr)

    if not plan:
        print(f"{PROG}: 登録対象がありません", file=sys.stderr)
        return 0

    if dry_run:
        print("[dry-run] 実際には登録・書き込みを行いません", file=sys.stderr)
        return 0

    if confirm and not confirm_start(len(plan)):
        print("Cancelled.", file=sys.stderr)
        return 1

    posted_count = 0
    failed_count = 0
    for seg, started, seconds in plan:
        try:
            worklog_jira_api.post_worklog(seg["ticket"], started, seconds, seg["note"], email, token)
        except worklog_jira_api.JiraApiError as e:
            print(f"{PROG}: 失敗: {seg['date']} {seg['ticket']}: {e}", file=sys.stderr)
            failed_count += 1
            continue
        seg["posted_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        posted_count += 1

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"{PROG}: {posted_count}件登録、{failed_count}件失敗", file=sys.stderr)
    if failed_count:
        print(f"{PROG}: 次にすべきこと: 失敗した要素を確認し、修正後に再実行してください(成功した要素は再投稿されません)", file=sys.stderr)
        return 1
    print("次にすべきこと: Jiraダッシュボード10011を開き、Timesheetガジェットに反映されているか確認してください", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
