import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import gcal_api

PROG = os.path.basename(__file__)
TIMEZONE = ZoneInfo("Asia/Tokyo")


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def format_time_field(field: dict) -> tuple[str, str]:
    """終日予定は"date"のみ、時刻指定の予定は"dateTime"を持つ。後者はJSTでdate/HH:MMに分解する。"""
    if "dateTime" in field:
        dt = datetime.fromisoformat(field["dateTime"]).astimezone(TIMEZONE)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    return field.get("date", ""), ""


def format_reminders(event: dict) -> list[str]:
    reminders = event.get("reminders", {})
    overrides = reminders.get("overrides", [])
    if not overrides:
        return ["default"] if reminders.get("useDefault") else []
    return [gcal_api.format_reminder_minutes(m) for m in sorted(o["minutes"] for o in overrides)]


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 2 or args[1] not in ("json", "tsv"):
        fail(f"usage: {PROG} <date> (json|tsv)")
    try:
        target_date = gcal_api.resolve_date(args[0])
    except ValueError:
        fail(f"invalid date: {args[0]!r} (expected TODAY, TOMORROW, or YYYY-MM-DD)")
    output_format = args[1]

    access_token = require_env("GOOGLE_ACCESS_TOKEN")
    calendar_id = require_env("GOOGLE_CALENDAR_ID")

    time_min = datetime.combine(target_date, datetime.min.time(), tzinfo=TIMEZONE)
    time_max = time_min + timedelta(days=1)
    query = urllib.parse.urlencode(
        {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
        }
    )

    try:
        result, _ = gcal_api.api_get(f"{gcal_api.events_path(calendar_id)}?{query}", access_token)
    except gcal_api.GcalApiError as e:
        fail(str(e))

    rows = []
    for event in result.get("items", []):
        if event.get("status") == "cancelled":
            continue
        event_date, event_time = format_time_field(event.get("start", {}))
        rows.append(
            {
                "id": event.get("id", ""),
                "date": event_date,
                "time": event_time,
                "title": event.get("summary", ""),
                "reminders": format_reminders(event),
            }
        )

    if output_format == "json":
        print(json.dumps(rows, ensure_ascii=False))
    else:
        for row in rows:
            reminders_text = ",".join(row["reminders"]) if row["reminders"] else "none"
            print("\t".join([row["id"], row["date"], row["time"], row["title"], reminders_text]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
