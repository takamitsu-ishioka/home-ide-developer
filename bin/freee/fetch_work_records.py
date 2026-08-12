#!/usr/bin/env python3
import calendar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

API_BASE_URL = "https://api.freee.co.jp/hr/api/v1"


def fail(message: str) -> None:
    print(f"fetch_work_records.py: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def target_dates(year_text: str, month_text: str) -> list[date]:
    try:
        year = int(year_text)
        month = int(month_text)
        first_day = date(year, month, 1)
    except ValueError:
        fail("year and month must be numeric, and month must be 1-12")

    today = date.today()
    this_month = date(today.year, today.month, 1)
    if first_day > this_month:
        fail("future month is not supported")

    last_day = calendar.monthrange(year, month)[1]
    end_day = today.day if first_day == this_month else last_day
    return [date(year, month, day) for day in range(1, end_day + 1)]


def print_failure(record_date: date, url: str, reason: str, body: bytes | None = None) -> None:
    print(f"fetch_work_records.py: failed to fetch work record for {record_date}; continuing", file=sys.stderr)
    print(f"fetch_work_records.py:   reason: {reason}", file=sys.stderr)
    print(f"fetch_work_records.py:   url: {url}", file=sys.stderr)
    if body:
        decoded = body.decode("utf-8", errors="replace").strip()
        if decoded:
            print("fetch_work_records.py:   response_body:", file=sys.stderr)
            for line in decoded.splitlines():
                print(f"    {line}", file=sys.stderr)


def fetch_one(access_token: str, employee_id: str, company_id: str, record_date: date) -> dict | None:
    query = urllib.parse.urlencode({"company_id": company_id})
    url = f"{API_BASE_URL}/employees/{employee_id}/work_records/{record_date.isoformat()}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = res.read()
            try:
                return json.loads(body)
            except json.JSONDecodeError as e:
                print_failure(record_date, url, f"invalid JSON response: {e}", body)
                return None
    except urllib.error.HTTPError as e:
        print_failure(record_date, url, f"HTTP {e.code} {e.reason}", e.read())
        return None
    except urllib.error.URLError as e:
        print_failure(record_date, url, f"network error: {e.reason}")
        return None
    except TimeoutError:
        print_failure(record_date, url, "request timed out")
        return None


def main() -> None:
    if len(sys.argv) < 3:
        fail("usage: fetch_work_records.py <year> <month>")

    access_token = require_env("FREEE_ACCESS_TOKEN")
    employee_id = require_env("FREEE_EMPLOYEE_ID")
    company_id = require_env("FREEE_COMPANY_ID")

    records = []
    for record_date in target_dates(sys.argv[1], sys.argv[2]):
        record = fetch_one(access_token, employee_id, company_id, record_date)
        if record is not None:
            records.append(record)

    json.dump(records, sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
