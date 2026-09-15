import json
import os
import sys
from datetime import date, datetime, timedelta

import worklog_jira_query

PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def resolve_date(date_text: str) -> date:
    try:
        return date.fromisoformat(date_text)
    except ValueError:
        fail(f"invalid date: {date_text} (expected YYYY-MM-DD)")


def duration_hm(begin: datetime, end: datetime) -> str:
    minutes = int((end - begin).total_seconds() // 60)
    return f"{minutes // 60}:{minutes % 60:02d}"


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    confirm = "--confirm" in args
    positional = [a for a in args if a not in ("--dry-run", "--confirm")]
    if len(positional) != 2:
        fail(f"usage: {PROG} <date> <file> [--dry-run] [--confirm]")
    target_date = resolve_date(positional[0])
    file_path = positional[1]

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    if os.path.exists(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                segments = json.load(f)
        except OSError as e:
            fail(f"{file_path}を読み取れません: {e}")
        except json.JSONDecodeError as e:
            fail(f"{file_path}のJSONを読み取れません: {e}")
    else:
        segments = []

    print("入力:", file=sys.stderr)
    print(f"  対象日 : {target_date.isoformat()}", file=sys.stderr)
    print(f"  保存先 : {file_path}", file=sys.stderr)
    print(file=sys.stderr)

    try:
        jira_entries = worklog_jira_query.fetch_all_worklogs(target_date, target_date, email, token)
    except worklog_jira_query.JiraApiError as e:
        fail(str(e))

    if not jira_entries:
        print(f"{PROG}: {target_date.isoformat()}のJira worklogが見つかりませんでした", file=sys.stderr)
        return 0

    # 投稿済み要素も含めて全て見る(未投稿要素だけを見ると、既に反映済みのticketを
    # 「ローカルに無い」と誤認して再実行のたびに重複追加してしまうため)。
    local_by_ticket: dict[str, list[dict]] = {}
    for seg in segments:
        if seg.get("date") == target_date.isoformat():
            local_by_ticket.setdefault(seg["ticket"], []).append(seg)

    by_ticket: dict[str, list[dict]] = {}
    for entry in jira_entries:
        by_ticket.setdefault(entry["issue"], []).append(entry)

    to_mark = []  # (既存要素, Jira worklog) -> 既存要素のposted_atを埋める
    to_append = []  # (ticket, Jira worklog) -> 新規要素を追加する
    ambiguous = []  # 1対1に対応付けられない -> 人間の確認が必要
    already_synced = 0  # ローカル要素が既に全て投稿済み -> 何もしない

    for ticket, entries in by_ticket.items():
        local_segs = local_by_ticket.get(ticket, [])
        unposted_segs = [s for s in local_segs if not s.get("posted_at")]
        if not local_segs:
            to_append.extend((ticket, e) for e in entries)
        elif not unposted_segs:
            already_synced += 1
        elif len(unposted_segs) == 1 and len(unposted_segs) == len(local_segs) and len(entries) == 1:
            to_mark.append((unposted_segs[0], entries[0]))
        else:
            ambiguous.append((ticket, local_segs, entries))

    to_append.sort(key=lambda pair: pair[1]["started"])

    print(
        f"{PROG}: Jira上の{target_date.isoformat()}のworklog: {len(jira_entries)}件({len(by_ticket)}チケット)",
        file=sys.stderr,
    )
    if already_synced:
        print(f"  [既に反映済み] {already_synced}チケット分は変更不要", file=sys.stderr)
    for seg, entry in to_mark:
        print(
            f"  [既存要素を投稿済みにする] {seg['date']} {seg['start']}-{seg['end']} {seg['ticket']} {seg['note']}",
            file=sys.stderr,
        )
    for ticket, entry in to_append:
        start_hm = entry["started"].strftime("%H:%M")
        end_hm = (entry["started"] + timedelta(seconds=entry["seconds"])).strftime("%H:%M")
        print(f"  [新規要素を追加] {target_date.isoformat()} {start_hm}-{end_hm} {ticket} {entry['comment']}", file=sys.stderr)
    for ticket, local_segs, entries in ambiguous:
        print(
            f"  [要手動確認] {ticket}: ローカル未投稿要素{len(local_segs)}件、Jira worklog{len(entries)}件で1対1に対応付けられません",
            file=sys.stderr,
        )
    print(file=sys.stderr)

    if dry_run:
        print("[dry-run] 実際には書き込みません", file=sys.stderr)
        return 0

    if confirm:
        print(f"{file_path}を更新しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
        answer = sys.stdin.readline()
        if not answer or answer.strip().lower() not in ("", "y", "yes"):
            print("Cancelled.", file=sys.stderr)
            return 1

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for seg, entry in to_mark:
        seg["posted_at"] = entry["created"] or now

    for ticket, entry in to_append:
        start_dt = entry["started"]
        end_dt = start_dt + timedelta(seconds=entry["seconds"])
        start_hm = start_dt.strftime("%H:%M")
        end_hm = end_dt.strftime("%H:%M")
        segments.append(
            {
                "date": target_date.isoformat(),
                "start": start_hm,
                "end": end_hm,
                "duration": duration_hm(start_dt, end_dt),
                "repo": "none",
                "ticket": ticket,
                "note": entry["comment"] or "[Jiraから同期]",
                "posted_at": entry["created"] or now,
                "turns": [],
            }
        )

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"{PROG}: {len(to_mark)}件を投稿済みに更新、{len(to_append)}件を新規追加しました", file=sys.stderr)
    if ambiguous:
        print(f"{PROG}: {len(ambiguous)}件は要手動確認のため変更していません(上記参照)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
