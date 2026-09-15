import json
import os
import re
import sys
from datetime import date, datetime

import worklog_jira_api

PROG = os.path.basename(__file__)
REQUIRED_FIELDS = ["date", "start", "end", "duration", "repo", "ticket", "ticket_url", "note"]
SENTINEL_TICKET_RE = re.compile(r"^_.*_$")  # 例: _nondeterministic_, _gap_ (実Jiraチケットではない未解決マーカー)


def duration_hm(begin: datetime, end: datetime) -> str:
    minutes = int((end - begin).total_seconds() // 60)
    return f"{minutes // 60}:{minutes % 60:02d}"


def validate_element(elem: dict) -> list[str]:
    errors = []
    for key in REQUIRED_FIELDS:
        if key not in elem:
            errors.append(f"必須フィールド{key!r}がありません")
    if errors:
        return errors  # フィールド欠落時は以降のチェックが無意味なのでここで打ち切る

    try:
        date.fromisoformat(elem["date"])
    except ValueError:
        errors.append(f"date形式が不正です: {elem['date']!r}")

    start_dt = None
    try:
        start_dt = datetime.strptime(elem["start"], "%H:%M")
    except ValueError:
        errors.append(f"start形式が不正です(HH:MM): {elem['start']!r}")

    end_dt = None
    try:
        end_dt = datetime.strptime(elem["end"], "%H:%M")
    except ValueError:
        errors.append(f"end形式が不正です(HH:MM): {elem['end']!r}")

    if start_dt is not None and end_dt is not None:
        if elem["end"] <= elem["start"]:
            errors.append(f"startがend以降になっています: start={elem['start']} end={elem['end']}")
        else:
            expected = duration_hm(start_dt, end_dt)
            if elem["duration"] != expected:
                errors.append(f"durationがstart/endと一致しません: duration={elem['duration']!r} 期待値={expected!r}")

    if not elem["repo"]:
        errors.append("repoが空です")

    if not elem["ticket"]:
        errors.append("ticketが空です")
    elif SENTINEL_TICKET_RE.match(elem["ticket"]):
        errors.append(
            f"ticketが未解決の特殊マーカーのままです: {elem['ticket']!r} "
            "(ticket_guess_rulesを追加するか、手で実ticketへ書き換えてください)"
        )
    else:
        expected_url = f"{worklog_jira_api.JIRA_BASE_URL}/browse/{elem['ticket']}"
        if elem["ticket_url"] != expected_url:
            errors.append(f"ticket_urlがticketと一致しません: ticket_url={elem['ticket_url']!r} 期待値={expected_url!r}")

    posted_at = elem.get("posted_at")
    if posted_at:
        try:
            datetime.fromisoformat(posted_at)
        except ValueError:
            errors.append(f"posted_atがISO日時形式ではありません: {posted_at!r}")

    return errors


def main() -> int:
    if sys.argv[1:]:
        print(f"{PROG}: Invalid arguments", file=sys.stderr)
        print(f"usage: {PROG} < segments.json", file=sys.stderr)
        return 1

    try:
        elements = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"{PROG}: stdinのJSONを読み取れません: {e}", file=sys.stderr)
        return 1

    if not isinstance(elements, list):
        print(f"{PROG}: 入力はJSON配列である必要があります", file=sys.stderr)
        return 1

    problems: list[tuple[int, str]] = []
    for i, elem in enumerate(elements):
        if not isinstance(elem, dict):
            problems.append((i, "要素がオブジェクトではありません"))
            continue
        for message in validate_element(elem):
            problems.append((i, message))

    prev_key = None
    last_end_by_date: dict[str, tuple[int, str]] = {}
    for i, elem in enumerate(elements):
        if not isinstance(elem, dict) or "date" not in elem or "start" not in elem:
            continue
        key = (elem["date"], elem["start"])
        if prev_key is not None and key < prev_key:
            problems.append((i, "date/startの昇順になっていません(前の要素より前の時刻です)"))
        prev_key = key

        prev = last_end_by_date.get(elem["date"])
        if prev is not None and elem.get("start", "") < prev[1]:
            problems.append(
                (i, f"直前の要素(end={prev[1]}、index={prev[0]})と時間帯が重なっています: start={elem['start']}")
            )
        if elem.get("end"):
            last_end_by_date[elem["date"]] = (i, elem["end"])

    if problems:
        problems.sort(key=lambda p: p[0])
        for i, message in problems:
            print(f"{PROG}: index {i}: {message}", file=sys.stderr)
        print(f"{PROG}: {len(problems)}件の問題があります。修正してから再実行してください", file=sys.stderr)
        return 1

    print(f"{PROG}: 問題なし({len(elements)}件)", file=sys.stderr)
    print(json.dumps(elements, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
