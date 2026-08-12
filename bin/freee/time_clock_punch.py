#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

import refresh_access_token

API_BASE_URL = "https://api.freee.co.jp/hr/api/v1"
VALID_TYPES = ["clock_in", "break_begin", "break_end", "clock_out"]
TYPE_LABELS = {
    "clock_in": "出勤",
    "break_begin": "休憩開始",
    "break_end": "休憩終了",
    "clock_out": "退勤",
}
PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def auth_hint(status: int) -> str:
    if status == 401:
        return " (アクセストークンが期限切れの可能性があります。./refresh_access_token.sh を実行してください)"
    return ""


def refresh_expired_token() -> str:
    env_path = refresh_access_token.default_env_path()
    try:
        updates = refresh_access_token.refresh(env_path)
    except Exception as e:
        fail(f"access_tokenが期限切れですが、自動更新に失敗しました: {e}{auth_hint(401)}")
    print(f"{PROG}: access_tokenが期限切れだったため自動更新しました({env_path})", file=sys.stderr)
    return updates["FREEE_ACCESS_TOKEN"]


def api_get(url: str, access_token: str, allow_refresh: bool = True) -> tuple[dict, str]:
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
        fail(f"GET {url} failed: HTTP {e.code} {e.reason}: {body}{auth_hint(e.code)}")


def api_post(url: str, access_token: str, body: dict, allow_refresh: bool = True) -> tuple[dict, str]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res), access_token
    except urllib.error.HTTPError as e:
        if e.code == 401 and allow_refresh:
            return api_post(url, refresh_expired_token(), body, allow_refresh=False)
        body_text = e.read().decode(errors="replace")
        fail(f"POST {url} failed: HTTP {e.code} {e.reason}: {body_text}{auth_hint(e.code)}")


def resolve_date(date_text: str) -> date:
    if date_text == "TODAY":
        return date.today()
    try:
        return date.fromisoformat(date_text)
    except ValueError:
        fail(f"invalid date: {date_text} (expected YYYY-MM-DD or TODAY)")


def format_types(types: list) -> str:
    if not types:
        return "なし"
    return ", ".join(f"{t} ({TYPE_LABELS[t]})" for t in types)


def print_summary(
    employee_id: str,
    company_id: str,
    punch_type: str,
    target_date: date,
    is_today: bool,
    punch_datetime: str | None,
    available_types: list,
) -> None:
    print("入力:", file=sys.stderr)
    print(f"  employee_id       : {employee_id}", file=sys.stderr)
    print(f"  company_id        : {company_id}", file=sys.stderr)
    print(f"  打刻種別          : {punch_type} ({TYPE_LABELS[punch_type]})", file=sys.stderr)
    print(f"  対象日            : {target_date.isoformat()}{' (TODAY)' if is_today else ''}", file=sys.stderr)
    if is_today:
        print("  打刻時刻          : 現在時刻(freeeサーバー側で記録)", file=sys.stderr)
    else:
        print(f"  打刻時刻          : {punch_datetime} (明示送信。当日以外の指定には管理者権限が必要)", file=sys.stderr)
    print(f"  対象日の打刻可能種別: {format_types(available_types)}", file=sys.stderr)
    print(file=sys.stderr)


def confirm_start() -> bool:
    print("打刻を実行しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
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
        fail(f"usage: {PROG} <type> <date> [--dry-run] [--confirm]")
    punch_type, date_text = positional
    if punch_type not in VALID_TYPES:
        fail(f"invalid type: {punch_type} (must be one of: {', '.join(VALID_TYPES)})")
    target_date = resolve_date(date_text)
    is_today = target_date == date.today()

    access_token = require_env("FREEE_ACCESS_TOKEN")
    employee_id = require_env("FREEE_EMPLOYEE_ID")
    company_id = require_env("FREEE_COMPANY_ID")

    punch_datetime = None
    if not is_today:
        punch_datetime = f"{target_date.isoformat()} {datetime.now().strftime('%H:%M:%S')}"

    types_url = (
        f"{API_BASE_URL}/employees/{employee_id}/time_clocks/available_types"
        f"?{urllib.parse.urlencode({'company_id': company_id, 'date': target_date.isoformat()})}"
    )
    types_result, access_token = api_get(types_url, access_token)
    available = types_result.get("available_types", [])

    print_summary(employee_id, company_id, punch_type, target_date, is_today, punch_datetime, available)

    if punch_type not in available:
        fail(
            f"'{punch_type} ({TYPE_LABELS[punch_type]})' は{target_date.isoformat()}時点で打刻できません"
            f"(打刻可能: {format_types(available)})。"
            f"多くの場合、既に'{punch_type}'が打刻済みであることを意味します(freee側では二重打刻を許可しません)。"
        )

    if confirm and not confirm_start():
        print("Cancelled.", file=sys.stderr)
        return 1

    body = {"company_id": int(company_id), "type": punch_type}
    if punch_datetime is not None:
        body["datetime"] = punch_datetime

    if dry_run:
        print("[dry-run] would POST:", file=sys.stderr)
        print(json.dumps(body, ensure_ascii=False, indent=2), file=sys.stderr)
        print(json.dumps({"dry_run": True, **body}, ensure_ascii=False))
        return 0

    create_url = f"{API_BASE_URL}/employees/{employee_id}/time_clocks"
    result, access_token = api_post(create_url, access_token, body)
    print(f"打刻を登録しました: {result.get('type')} at {result.get('datetime')}", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
