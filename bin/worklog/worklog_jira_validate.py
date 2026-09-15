import json
import os
import subprocess
import sys
import unicodedata
from datetime import date, datetime, timedelta

import worklog_jira_query

PROG = os.path.basename(__file__)
DEFAULT_TICKET = "GENERAL-451"
FREEE_DIR = os.path.expanduser("~/bin/freee")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")

# ステータスは独立した2つの軸に分解する(1本の文言に混ぜない):
#   local_state: local列の中身がどんな性質のデータか
#   match      : remoteとlocalの値が比較可能な場合、一致するか
ALL_LOCAL_STATES = ("posted", "unposted", "mixed", "none")
ALL_MATCHES = ("match", "mismatch", "-")

GUIDANCE = {
    ("posted", "mismatch"): (
        "ローカル(投稿済み)・Jiraの両方に記録がありますが、時間が一致しません。"
        "Jira側のissue画面で「作業ログを表示」から実際の登録内容を確認し、"
        "bin/worklog/log/<date>.jsonの入力ミスかJira側の修正漏れかを判断してください。"
        "正しい方に合わせて、誤っている方を手動で修正してください。"
    ),
    ("posted", "-"): (
        "bin/worklog/log/<date>.json上はposted_at済み(=過去にPOST成功したはず)なのに、"
        "今はJiraに該当の記録が見当たりません。Jira側でその作業ログが後から削除された可能性があります。"
        "Jira側のissue画面で作業ログ履歴を確認し、無ければworklog_jira_post_batch.shで再投稿するか、"
        "posted_atを手動で空にしてから再投稿してください。"
    ),
    ("unposted", "match"): (
        "bin/worklog/log/<date>.jsonは未投稿のままですが、Jiraには既に同じ時間の記録があります。"
        "既に別経路(手動投稿など)で登録済みと考えられます。"
        "worklog_jira_sync.sh <date> <file> --confirm を実行してposted_atを埋めてください"
        "(このまま一括投稿すると二重登録になります)。"
    ),
    ("unposted", "mismatch"): (
        "bin/worklog/log/<date>.jsonは未投稿のままですが、Jiraには既に(異なる時間で)記録があります。"
        "同じ作業の一部だけが投稿済みなのか、別の作業なのかを人間が判断する必要があります。"
        "worklog_jira_sync.shは自動判定しません。手動でファイルかJira側を確認してください。"
    ),
    ("mixed", "match"): (
        "同じdate+ticketに投稿済み要素と未投稿要素の両方がローカルにあります(合計はJiraと一致)。"
        "個々の要素のどれが投稿済みでどれが未投稿かをbin/worklog/log/<date>.jsonで直接確認し、"
        "未投稿の要素だけ重複が無いか手動で判断してください。"
    ),
    ("mixed", "mismatch"): (
        "同じdate+ticketに投稿済み要素と未投稿要素の両方がローカルにあり、合計がJiraとも一致しません。"
        "bin/worklog/log/<date>.jsonの該当date+ticketの要素を直接開いて、"
        "投稿済み・未投稿それぞれの内容を確認してください。"
    ),
    ("mixed", "-"): (
        "同じdate+ticketに投稿済み要素と未投稿要素の両方がローカルにありますが、Jiraには記録がありません。"
        "bin/worklog/log/<date>.jsonの該当date+ticketの要素を直接開いて、"
        "投稿済みのはずの要素が本当に投稿されているか確認してください。"
    ),
}


# 問題として扱う(non-zero終了・強調表示の対象とする)組み合わせ
def is_problem(local_state: str, match: str, remote_present: bool) -> bool:
    if match == "mismatch":
        return True
    if local_state == "mixed":
        return True
    if local_state == "posted" and not remote_present:
        return True
    if local_state == "unposted" and match == "match":
        return True
    return False


# ticketレベルの記録が一件も無いdateの分類(freeeのwork_recordから判定する第3の軸)。
# local_state/matchとは独立した軸(その日ticket単位の記録が皆無だった理由)なので、
# 同じ列に混ぜず`status`という別列にする。freeeはここでは「作業時間の外枠」としてではなく、
# 「その日の勤怠区分(勤務/休日/休暇)を読む」目的でのみ参照する(design.mdのfreee方針転換と矛盾しない)。
DAY_STATUSES = ("work", "holiday_public", "holiday_private", "absence", "not_posted_yet", "unknown")
PROBLEM_DAY_STATUSES = ("not_posted_yet", "unknown")

DAY_GUIDANCE = {
    "not_posted_yet": (
        "freeeの打刻上は勤務日(出勤あり)ですが、この日に関するbin/worklog/log/<date>.json・Jiraの記録が一件もありません。"
        "worklog_session_turns_list.sh <date> none | worklog_session_infer.sh でセッションログから推測し、"
        "内容を確認の上bin/worklog/log/<date>.jsonへ保存してください。"
    ),
    "unknown": (
        "freeeの打刻・勤怠区分からこの日の状態を判定できませんでした。"
        "freee側でこの日の勤怠(出勤/休日/休暇)が正しく記録されているか確認してください。"
    ),
}


def classify_day(date_text: str) -> str:
    """ticketレベルの記録が一件も無いdateについて、freeeのwork_recordから状態を分類する。

    day_pattern(prescribed_holiday/legal_holiday)は会社側が定める休日(public)、
    paid_holiday等はその日自体は勤務日だが本人が休暇を取得した状態(private)を表す。
    """
    result = subprocess.run(
        [os.path.join(FREEE_DIR, "work_record_get.sh"), date_text],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "unknown"
    try:
        record = json.loads(result.stdout)
    except json.JSONDecodeError:
        return "unknown"

    if record.get("day_pattern") in ("prescribed_holiday", "legal_holiday"):
        return "holiday_public"
    if record.get("is_absence"):
        return "absence"
    if (record.get("paid_holiday") or 0) > 0 or record.get("paid_holidays") or (record.get("special_holiday") or 0) > 0:
        return "holiday_private"
    if record.get("clock_in_at"):
        return "not_posted_yet"
    return "unknown"


RED = "\033[1;31m"
RESET = "\033[0m"


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


def seconds_between(date_text: str, start_hm: str, end_hm: str) -> int:
    start = datetime.strptime(f"{date_text} {start_hm}", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{date_text} {end_hm}", "%Y-%m-%d %H:%M")
    return int((end - start).total_seconds())


def load_local_segments(from_date: date, to_date: date) -> list[dict]:
    """bin/worklog/log/<date>.json群のうち、期間内に存在するものだけ読み込んで結合する。"""
    segments: list[dict] = []
    d = from_date
    while d <= to_date:
        path = os.path.join(LOG_DIR, f"{d.isoformat()}.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    segments.extend(json.load(f))
            except (OSError, json.JSONDecodeError) as e:
                fail(f"{path}を読み取れません: {e}")
        d += timedelta(days=1)
    return segments


def strip_tag_prefixes(text: str) -> str:
    """先頭の"[FEATURE]"のような情報の少ないタグ表記を取り除く(複数連続も対象)。"""
    while text.startswith("["):
        close = text.find("]")
        if close == -1:
            break
        text = text[close + 1 :].lstrip()
    return text


def display_width(text: str) -> int:
    """東アジア幅を考慮した表示上の桁数(全角2・半角1)。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def fit_display(text: str, width: int) -> str:
    """表示幅がwidthになるよう、切り詰め(...)またはスペース埋めをする。"""
    if display_width(text) <= width:
        return text + " " * (width - display_width(text))
    budget = width - 3  # "..."分を確保
    truncated = ""
    current = 0
    for c in text:
        w = 2 if unicodedata.east_asian_width(c) in "WF" else 1
        if current + w > budget:
            break
        truncated += c
        current += w
    result = truncated + "..."
    return result + " " * (width - display_width(result))


def format_hm(seconds: int) -> str:
    if seconds == 0:
        return "none"
    minutes = seconds // 60
    return f"{minutes // 60}:{minutes % 60:02d}"


# 列名の表示上のx座標をヘッダ・値で揃えるため、各列を固定幅にする(fit_display()で
# 切り詰め/パディング)。TSVとしては厳密ではなくなるが、これは人間が見る出力なので許容する。
COLUMN_WIDTHS = {
    "flag": len("flag"),
    "date": max(len("date"), len("YYYY-MM-DD")),
    "ticket": max(len("ticket"), 14),  # 例: INTEGRATED-1234
    "ticket_description": len("ticket_description"),
    "remote": max(len("remote"), 8),  # 例: 123:45
    "local": max(len("local"), 8),
    "local_state": max(len("local_state"), max(display_width(s) for s in ALL_LOCAL_STATES)),
    "match": max(len("match"), max(display_width(s) for s in ALL_MATCHES)),
    "status": max(len("status"), max(display_width(s) for s in DAY_STATUSES)),
}
COLUMNS = ("date", "ticket", "ticket_description", "remote", "local", "local_state", "match", "status")


def col(name: str, text: str) -> str:
    return fit_display(text, COLUMN_WIDTHS[name])


def main() -> int:
    if len(sys.argv) != 3:
        fail(f"usage: {PROG} <from_date> <to_date>")
    from_date = resolve_date(sys.argv[1])
    to_date = resolve_date(sys.argv[2])
    if from_date > to_date:
        fail(f"from_date({from_date.isoformat()}) must not be after to_date({to_date.isoformat()})")

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    print("入力:", file=sys.stderr)
    print(f"  期間   : {from_date.isoformat()} 〜 {to_date.isoformat()}", file=sys.stderr)
    print(f"  対象   : {LOG_DIR}/<date>.json と Jira worklog(自分の分)", file=sys.stderr)
    print(file=sys.stderr)

    try:
        jira_entries = worklog_jira_query.fetch_all_worklogs(from_date, to_date, email, token)
    except worklog_jira_query.JiraApiError as e:
        fail(str(e))

    # Jira側の秒はJiraのUI上分単位入力が普通だが、念のため分未満の端数を切り捨て、
    # 切り捨てた分をその日のdefault(GENERAL-451)へ加算する(合計時間を失わないため)。
    remote_totals: dict[tuple[str, str], int] = {}
    remainder_by_date: dict[str, int] = {}
    for e in jira_entries:
        key = (e["date"].isoformat(), e["issue"])
        minutes, remainder = divmod(e["seconds"], 60)
        remote_totals[key] = remote_totals.get(key, 0) + minutes * 60
        if remainder:
            remainder_by_date[key[0]] = remainder_by_date.get(key[0], 0) + remainder
    for date_text, remainder in remainder_by_date.items():
        # 端数の合計が60秒以上になることもあるため、ここでも分単位に丸める
        key = (date_text, DEFAULT_TICKET)
        remote_totals[key] = remote_totals.get(key, 0) + (remainder // 60) * 60

    local_posted: dict[tuple[str, str], int] = {}
    local_unposted: dict[tuple[str, str], int] = {}
    for seg in load_local_segments(from_date, to_date):
        if not (from_date.isoformat() <= seg["date"] <= to_date.isoformat()):
            continue
        if not seg.get("end"):
            continue
        seconds = seconds_between(seg["date"], seg["start"], seg["end"])
        key = (seg["date"], seg["ticket"])
        target = local_posted if seg.get("posted_at") else local_unposted
        target[key] = target.get(key, 0) + seconds

    all_keys = sorted(set(local_posted) | set(local_unposted) | set(remote_totals))

    try:
        summaries = worklog_jira_query.fetch_summaries([t for _, t in all_keys], email, token)
    except worklog_jira_query.JiraApiError as e:
        fail(str(e))
    descriptions = {ticket: strip_tag_prefixes(summary) for ticket, summary in summaries.items()}

    # ticketレベルの記録が一件も無いdateについて、freeeの勤怠区分(勤務/休日/休暇/未投稿)を分類する
    covered_dates = {d for d, _ in all_keys}
    missing_dates = []
    d = from_date
    while d <= to_date:
        if d.isoformat() not in covered_dates:
            missing_dates.append(d.isoformat())
        d += timedelta(days=1)

    rows = []  # (date_text, values dict, problem: bool, guidance: str|None)
    for key in all_keys:
        date_text, ticket = key
        lp = local_posted.get(key, 0)
        lu = local_unposted.get(key, 0)
        rt = remote_totals.get(key, 0)
        local_total = lp + lu

        if lp and lu:
            local_state = "mixed"
        elif lp:
            local_state = "posted"
        elif lu:
            local_state = "unposted"
        else:
            local_state = "none"

        if local_state in ("none", "mixed") or rt == 0:
            match = "-"
            # mixedの場合も、参考として合計(lp+lu)とremoteの一致有無だけは表示に活かす
            if local_state == "mixed" and rt:
                match = "match" if local_total == rt else "mismatch"
        else:
            local_value = lp or lu
            match = "match" if local_value == rt else "mismatch"

        problem = is_problem(local_state, match, remote_present=rt > 0)
        values = {
            "date": date_text,
            "ticket": ticket,
            "ticket_description": descriptions.get(ticket, ""),
            "remote": format_hm(rt),
            "local": format_hm(local_total),
            "local_state": local_state,
            "match": match,
            "status": "work",
        }
        guidance = GUIDANCE[(local_state, match)] if problem else None
        rows.append((date_text, values, problem, guidance))

    for date_text in missing_dates:
        day_status = classify_day(date_text)
        problem = day_status in PROBLEM_DAY_STATUSES
        values = {
            "date": date_text,
            "ticket": "-",
            "ticket_description": "-",
            "remote": "-",
            "local": "-",
            "local_state": "-",
            "match": "-",
            "status": day_status,
        }
        guidance = DAY_GUIDANCE[day_status] if problem else None
        rows.append((date_text, values, problem, guidance))

    rows.sort(key=lambda r: r[0])

    isatty = sys.stdout.isatty()
    # ttyならANSIカラーで問題行を強調する。tty出ない(エスケープシーケンスが効かない)場合は、
    # 行頭に問題有無を示す1文字(-/*)を付けて、色に頼らず視覚的に区別できるようにする。
    columns = ("flag", *COLUMNS) if not isatty else COLUMNS
    print(" ".join(col(name, name) for name in columns))
    problems: list[tuple[str, str, str]] = []  # (date_text, label, guidance)
    for date_text, values, problem, guidance in rows:
        if problem:
            label = f"{values['ticket']}: local_state={values['local_state']} match={values['match']}"
            if values["ticket"] == "-":
                label = f"status={values['status']}"
            problems.append((date_text, label, guidance))

        row_values = dict(values)
        if not isatty:
            row_values["flag"] = "*" if problem else "-"
        line = " ".join(col(name, row_values[name]) for name in columns)
        print(f"{RED}{line}{RESET}" if (isatty and problem) else line)

    print(
        f"{PROG}: {from_date.isoformat()}〜{to_date.isoformat()}を検査、{len(rows)}件中{len(problems)}件が要確認",
        file=sys.stderr,
    )
    if problems:
        print(file=sys.stderr)
        print("要確認の内訳:", file=sys.stderr)
        for date_text, label, guidance in problems:
            print(f"  {date_text} {label}", file=sys.stderr)
            print(f"    -> {guidance}", file=sys.stderr)
        return 1
    print("次にすべきこと: 「Jiraのみ」の行があればworklog_jira_sync.sh <date> <file>で取り込んでください", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
