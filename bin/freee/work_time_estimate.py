#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

import refresh_access_token

API_BASE_URL = "https://api.freee.co.jp/hr/api/v1"
PROG = os.path.basename(__file__)
JST = timezone(timedelta(hours=9))


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def refresh_expired_token() -> str:
    env_path = refresh_access_token.default_env_path()
    try:
        updates = refresh_access_token.refresh(env_path)
    except Exception as e:
        fail(f"access_tokenが期限切れですが、自動更新に失敗しました: {e}")
    print(f"{PROG}: access_tokenが期限切れだったため自動更新しました({env_path})", file=sys.stderr)
    return updates["FREEE_ACCESS_TOKEN"]


def api_get(url: str, access_token: str, allow_refresh: bool = True) -> tuple[list, str]:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res), access_token
    except urllib.error.HTTPError as e:
        if e.code == 401 and allow_refresh:
            return api_get(url, refresh_expired_token(), allow_refresh=False)
        body = e.read().decode(errors="replace")
        fail(f"GET {url} failed: HTTP {e.code} {e.reason}: {body}")


def fmt_hm(dt: datetime) -> str:
    return dt.astimezone(JST).strftime("%H:%M")


def fmt_dur(mins: int) -> str:
    sign = "-" if mins < 0 else ""
    mins = abs(mins)
    return f"{sign}{mins // 60}h {mins % 60:02d}m"


def main() -> int:
    if len(sys.argv) != 1:
        fail(f"usage: {PROG} (引数なし。本日・現在時刻のみを対象とする)")

    access_token = require_env("FREEE_ACCESS_TOKEN")
    employee_id = require_env("FREEE_EMPLOYEE_ID")
    company_id = require_env("FREEE_COMPANY_ID")

    today = date.today()
    now = datetime.now(JST)

    # work_records(日次集計)はtime_clocks(打刻イベント一覧)に対して反映が遅れることがあるため、
    # 「今」を扱うこのスクリプトはtime_clocksを直接参照する。
    url = (
        f"{API_BASE_URL}/employees/{employee_id}/time_clocks"
        f"?{urllib.parse.urlencode({'company_id': company_id, 'from_date': today.isoformat(), 'to_date': today.isoformat()})}"
    )
    events, access_token = api_get(url, access_token)
    events = sorted(events, key=lambda e: e["datetime"])

    clock_in = next((e for e in events if e["type"] == "clock_in"), None)
    if clock_in is None:
        fail(f"本日({today.isoformat()})はまだ出勤(clock_in)の打刻がありません")

    clock_in_dt = datetime.fromisoformat(clock_in["datetime"])
    clock_out = next((e for e in events if e["type"] == "clock_out"), None)
    already_clocked_out = clock_out is not None
    end_dt = datetime.fromisoformat(clock_out["datetime"]) if already_clocked_out else now

    break_mins = 0
    break_lines = []
    pending_begin = None
    for e in events:
        if e["type"] == "break_begin":
            pending_begin = datetime.fromisoformat(e["datetime"])
        elif e["type"] == "break_end" and pending_begin is not None:
            b_end = datetime.fromisoformat(e["datetime"])
            break_mins += int((b_end - pending_begin).total_seconds() // 60)
            break_lines.append(f"{fmt_hm(pending_begin)}-{fmt_hm(b_end)}")
            pending_begin = None
    on_break = pending_begin is not None and not already_clocked_out
    if pending_begin is not None:
        # 現在休憩中(または、clock_out済みなのにbreak_endが無い異常系)。
        # end_dt(clock_out時刻、または今)を休憩終了とみなして計算する。
        break_mins += int((end_dt - pending_begin).total_seconds() // 60)
        break_lines.append(f"{fmt_hm(pending_begin)}-{fmt_hm(end_dt)}(休憩中)")

    worked_mins = max(int((end_dt - clock_in_dt).total_seconds() // 60) - break_mins, 0)

    print(f"対象日   : {today.isoformat()}")
    print(f"出勤     : {fmt_hm(clock_in_dt)}")
    if break_lines:
        print(f"休憩     : {', '.join(break_lines)} (計 {fmt_dur(break_mins)})")
    else:
        print("休憩     : なし")
    if already_clocked_out:
        print(f"退勤     : {fmt_hm(end_dt)} (打刻済み)")
    else:
        print(f"現在時刻 : {fmt_hm(now)}")
    if on_break:
        print("(現在休憩中。休憩を今終えず、この瞬間に退勤したと仮定した場合の見込みです)")
    print()

    if already_clocked_out:
        print(f"本日は既に退勤済みです。実労働時間: {fmt_dur(worked_mins)}")
    else:
        print(f"今、退勤の打刻をした場合の労働時間: {fmt_dur(worked_mins)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
