import os
import sys

import gcal_api

PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def confirm_start(event_id: str) -> bool:
    print(f"予定(id={event_id})を削除しますか？ (Y/n): ", end="", file=sys.stderr, flush=True)
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
    if len(positional) != 1:
        fail(f"usage: {PROG} <event_id> [--dry-run] [--confirm]")
    event_id = positional[0]

    access_token = require_env("GOOGLE_ACCESS_TOKEN")
    calendar_id = require_env("GOOGLE_CALENDAR_ID")

    print("入力:", file=sys.stderr)
    print(f"  カレンダー: {calendar_id}", file=sys.stderr)
    print(f"  event_id : {event_id}", file=sys.stderr)
    print(file=sys.stderr)

    if dry_run:
        print("[dry-run] 実際には削除しません", file=sys.stderr)
        return 0

    if confirm and not confirm_start(event_id):
        print("Cancelled.", file=sys.stderr)
        return 1

    try:
        gcal_api.api_delete(gcal_api.event_path(calendar_id, event_id), access_token)
    except gcal_api.GcalApiError as e:
        fail(str(e))

    print(f"{PROG}: 削除しました(id={event_id})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
