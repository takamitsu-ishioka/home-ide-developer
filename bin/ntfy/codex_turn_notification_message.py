import json
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(
            f"usage: {sys.argv[0]} '<codex_notification_json>'",
            file=sys.stderr,
        )
        return 1

    try:
        notification = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"invalid Codex notification JSON: {exc}", file=sys.stderr)
        return 1

    if notification.get("type") != "agent-turn-complete":
        return 0

    print("Codexの作業が完了しました。確認してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
