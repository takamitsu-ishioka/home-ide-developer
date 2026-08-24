import os
import sys

import gcal_api

PROG = os.path.basename(__file__)
METHOD = "popup"


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def confirm_start(event_id: str, reminder_text: str) -> bool:
    print(f"予定(id={event_id})に通知({reminder_text}前)を追加しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
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
        fail(f"usage: {PROG} <event_id> <reminder> [--dry-run] [--confirm]")
    event_id, reminder_text = positional

    try:
        minutes = gcal_api.parse_reminder_minutes(reminder_text)
    except ValueError:
        fail(f"reminderの形式が不正です(HH:MM。予定の何時間何分前か): {reminder_text!r}")

    access_token = require_env("GOOGLE_ACCESS_TOKEN")
    calendar_id = require_env("GOOGLE_CALENDAR_ID")

    try:
        event, access_token = gcal_api.api_get(gcal_api.event_path(calendar_id, event_id), access_token)
    except gcal_api.GcalApiError as e:
        fail(str(e))

    overrides = event.get("reminders", {}).get("overrides", [])

    print("入力:", file=sys.stderr)
    print(f"  カレンダー  : {calendar_id}", file=sys.stderr)
    print(f"  event_id   : {event_id} ({event.get('summary', '')})", file=sys.stderr)
    print(f"  現在の通知  : {gcal_api.format_overrides(overrides)}", file=sys.stderr)
    print(f"  追加する通知: {METHOD}:{reminder_text}", file=sys.stderr)
    print(file=sys.stderr)

    if any(o.get("method") == METHOD and o.get("minutes") == minutes for o in overrides):
        print(f"{PROG}: 既に同じ通知({reminder_text}前)が設定されています。変更しません", file=sys.stderr)
        return 0

    if dry_run:
        print("[dry-run] 実際には追加しません", file=sys.stderr)
        return 0

    if confirm and not confirm_start(event_id, reminder_text):
        print("Cancelled.", file=sys.stderr)
        return 1

    new_overrides = overrides + [{"method": METHOD, "minutes": minutes}]
    body = {"reminders": {"useDefault": False, "overrides": new_overrides}}
    try:
        gcal_api.api_patch(gcal_api.event_path(calendar_id, event_id), access_token, body)
    except gcal_api.GcalApiError as e:
        fail(str(e))

    print(f"{PROG}: 通知({reminder_text}前)を追加しました(id={event_id})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
