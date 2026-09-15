#!/usr/bin/env bash
# Convert a Codex agent-turn-complete JSON payload into a safe ntfy notification.
# Deliberately excludes prompts, assistant text, paths, and source code from the notification.
set -euo pipefail

SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$#" -ne 1 ]; then
  echo "$SCRIPT_NAME: Invalid arguments" >&2
  echo "usage: $SCRIPT_NAME '<codex_notification_json>'" >&2
  echo "example: $SCRIPT_NAME '{\"type\":\"agent-turn-complete\"}'" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/, ""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  echo "Next: configure this script as the user-level Codex notify command." >&2
  exit 1
fi

if ! message="$(python3 "$SCRIPT_DIR/codex_turn_notification_message.py" "$1")"; then
  echo "$SCRIPT_NAME: Could not parse the Codex notification; notification skipped." >&2
  echo "Next: inspect the Codex notify payload and retry the adapter manually." >&2
  exit 0
fi

if [ -z "$message" ]; then
  exit 0
fi

if ! "$SCRIPT_DIR/ntfy_notification_send.sh" "$message"; then
  echo "$SCRIPT_NAME: ntfy delivery failed, but the completed Codex turn is unaffected." >&2
  echo "Next: run ntfy_notification_send.sh manually after checking its configuration." >&2
fi

exit 0
