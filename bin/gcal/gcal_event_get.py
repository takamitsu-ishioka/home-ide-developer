import os
import sys
from datetime import datetime
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


def format_reminders(event: dict) -> str:
    reminders = event.get("reminders", {})
    overrides = reminders.get("overrides", [])
    if not overrides and reminders.get("useDefault"):
        return "default"
    return gcal_api.format_overrides(overrides)


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 1:
        fail(f"usage: {PROG} <event_id>")
    event_id = args[0]

    access_token = require_env("GOOGLE_ACCESS_TOKEN")
    calendar_id = require_env("GOOGLE_CALENDAR_ID")

    try:
        event, _ = gcal_api.api_get(gcal_api.event_path(calendar_id, event_id), access_token)
    except gcal_api.GcalApiError as e:
        fail(str(e))

    start_date, start_hm = format_time_field(event.get("start", {}))
    _, end_hm = format_time_field(event.get("end", {}))

    print(
        "\t".join(
            [
                event.get("id", ""),
                start_date,
                start_hm,
                end_hm,
                event.get("summary", ""),
                format_reminders(event),
                event.get("status", ""),
            ]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
