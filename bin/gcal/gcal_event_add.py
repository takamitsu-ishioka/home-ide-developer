import os
import sys
from datetime import datetime

import gcal_api

PROG = os.path.basename(__file__)
TIMEZONE = "Asia/Tokyo"


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def confirm_start() -> bool:
    print("この予定を登録しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
    answer = sys.stdin.readline()
    if not answer:
        print("Cancelled: no input available (non-interactive)", file=sys.stderr)
        return False
    return answer.strip().lower() in ("", "y", "yes")


def build_reminders(reminder_text: str) -> dict:
    if reminder_text == "none":
        return {"useDefault": False, "overrides": []}
    try:
        minutes = gcal_api.parse_reminder_minutes(reminder_text)
    except ValueError:
        fail(f"reminderの形式が不正です(HH:MMまたはnone): {reminder_text!r}")
    return {"useDefault": False, "overrides": [{"method": "popup", "minutes": minutes}]}


def main() -> int:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    confirm = "--confirm" in args
    positional = [a for a in args if a not in ("--dry-run", "--confirm")]
    if len(positional) != 5:
        fail(f"usage: {PROG} <date> <start_hm> <end_hm> <reminder> <title> [--dry-run] [--confirm]")
    date_text, start_hm, end_hm, reminder_text, summary = positional

    try:
        date_text = gcal_api.resolve_date(date_text).isoformat()
    except ValueError:
        fail(f"invalid date: {date_text!r} (expected TODAY, TOMORROW, or YYYY-MM-DD)")

    try:
        datetime.strptime(start_hm, "%H:%M")
        datetime.strptime(end_hm, "%H:%M")
    except ValueError as e:
        fail(f"start_hm/end_hmの形式が不正です: {e}")

    if end_hm <= start_hm:
        fail(f"start({start_hm})がend({end_hm})以降になっています")

    reminders = build_reminders(reminder_text)

    access_token = require_env("GOOGLE_ACCESS_TOKEN")
    calendar_id = require_env("GOOGLE_CALENDAR_ID")

    body = {
        "summary": summary,
        "start": {"dateTime": f"{date_text}T{start_hm}:00", "timeZone": TIMEZONE},
        "end": {"dateTime": f"{date_text}T{end_hm}:00", "timeZone": TIMEZONE},
        "reminders": reminders,
    }

    print("入力:", file=sys.stderr)
    print(f"  カレンダー: {calendar_id}", file=sys.stderr)
    print(f"  日時     : {date_text} {start_hm}-{end_hm} ({TIMEZONE})", file=sys.stderr)
    print(f"  タイトル : {summary}", file=sys.stderr)
    print(f"  通知     : {reminder_text}", file=sys.stderr)
    print(file=sys.stderr)

    if dry_run:
        print("[dry-run] 実際には登録しません", file=sys.stderr)
        return 0

    if confirm and not confirm_start():
        print("Cancelled.", file=sys.stderr)
        return 1

    try:
        event, _ = gcal_api.api_post(gcal_api.events_path(calendar_id), access_token, body)
    except gcal_api.GcalApiError as e:
        fail(str(e))

    print("\t".join([event.get("id", ""), date_text, start_hm, end_hm, summary]))
    print(f"{PROG}: 登録しました(id={event.get('id')}) {event.get('htmlLink', '')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
