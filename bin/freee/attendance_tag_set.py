#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

import refresh_access_token

API_BASE_URL = "https://api.freee.co.jp/hr/api/v1"
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


def api_put(url: str, access_token: str, body: dict, allow_refresh: bool = True) -> tuple[dict, str]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res), access_token
    except urllib.error.HTTPError as e:
        if e.code == 401 and allow_refresh:
            return api_put(url, refresh_expired_token(), body, allow_refresh=False)
        body_text = e.read().decode(errors="replace")
        fail(f"PUT {url} failed: HTTP {e.code} {e.reason}: {body_text}{auth_hint(e.code)}")


def resolve_date(date_text: str) -> date:
    if date_text == "TODAY":
        return date.today()
    try:
        return date.fromisoformat(date_text)
    except ValueError:
        fail(f"invalid date: {date_text} (expected YYYY-MM-DD or TODAY)")


def find_tag(tags: list, tag_name: str) -> dict | None:
    for t in tags:
        if t.get("name") == tag_name:
            return t
    return None


def confirm_start() -> bool:
    print("勤怠タグを更新しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
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

    if len(positional) != 3:
        fail(f"usage: {PROG} <date> <tag_name> <amount>")
    date_text, tag_name, amount_text = positional
    target_date = resolve_date(date_text)

    try:
        amount = int(amount_text)
        if amount < 0:
            raise ValueError
    except ValueError:
        fail(f"invalid amount: {amount_text} (expected an integer >= 0)")

    access_token = require_env("FREEE_ACCESS_TOKEN")
    employee_id = require_env("FREEE_EMPLOYEE_ID")
    company_id = require_env("FREEE_COMPANY_ID")

    tags_url = (
        f"{API_BASE_URL}/employees/{employee_id}/attendance_tags"
        f"?{urllib.parse.urlencode({'company_id': company_id})}"
    )
    tags_result, access_token = api_get(tags_url, access_token)
    available_tags = tags_result.get("employee_attendance_tags", [])
    target_tag = find_tag(available_tags, tag_name)
    if target_tag is None:
        names = ", ".join(t.get("name", "?") for t in available_tags) or "(なし)"
        fail(f"勤怠タグ '{tag_name}' が見つかりません(利用可能な勤怠タグ: {names})")
    if not target_tag.get("is_employee_usable", True):
        fail(f"勤怠タグ '{tag_name}' はこの従業員には利用できません")
    if amount > target_tag.get("max_amount", amount):
        fail(f"amount={amount} は勤怠タグ '{tag_name}' の上限(max_amount={target_tag['max_amount']})を超えています")

    day_url = (
        f"{API_BASE_URL}/employees/{employee_id}/attendance_tags/{target_date.isoformat()}"
        f"?{urllib.parse.urlencode({'company_id': company_id})}"
    )
    day_result, access_token = api_get(day_url, access_token)
    assigned = day_result.get("employee_attendance_tags", [])

    merged = {a["attendance_tag"]["id"]: a["amount"] for a in assigned}
    before_amount = merged.get(target_tag["id"], 0)
    merged[target_tag["id"]] = amount

    other_tags = [
        f"{a['attendance_tag']['name']}={a['amount']}"
        for a in assigned
        if a["attendance_tag"]["id"] != target_tag["id"]
    ]

    print("入力:", file=sys.stderr)
    print(f"  employee_id           : {employee_id}", file=sys.stderr)
    print(f"  company_id            : {company_id}", file=sys.stderr)
    print(f"  date                  : {target_date.isoformat()}", file=sys.stderr)
    print(f"  tag                   : {tag_name} (id={target_tag['id']}, max_amount={target_tag['max_amount']})", file=sys.stderr)
    print(f"  amount                : {before_amount} -> {amount}", file=sys.stderr)
    print(f"  その日の他の勤怠タグ(維持): {', '.join(other_tags) if other_tags else '(なし)'}", file=sys.stderr)
    print(file=sys.stderr)

    if confirm and not confirm_start():
        print("Cancelled.", file=sys.stderr)
        return 1

    body = {
        "company_id": int(company_id),
        "employee_attendance_tags": [
            {"attendance_tag_id": tag_id, "amount": amt} for tag_id, amt in merged.items()
        ],
    }

    if dry_run:
        print("[dry-run] would PUT:", file=sys.stderr)
        print(json.dumps(body, ensure_ascii=False, indent=2), file=sys.stderr)
        print(json.dumps({"dry_run": True, **body}, ensure_ascii=False))
        return 0

    result, access_token = api_put(day_url, access_token, body)
    print(f"勤怠タグを更新しました: {tag_name}={amount} ({target_date.isoformat()})", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
