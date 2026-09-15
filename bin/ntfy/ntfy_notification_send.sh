#!/usr/bin/env bash
# Send one short, non-sensitive message to a configured ntfy topic.
# Reads configuration from the .env file next to this script.
set -euo pipefail

SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

usage() {
  echo "$SCRIPT_NAME: $1" >&2
  echo "usage: $SCRIPT_NAME <message> [--dry-run] [--confirm]" >&2
  echo "example: $SCRIPT_NAME 'Codexの作業が完了しました'" >&2
  echo "example: printf '%s\\n' 'バックアップ完了' | $SCRIPT_NAME" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/, ""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  echo "Next: copy $SCRIPT_DIR/.env.template to $ENV_FILE, edit it, and run chmod 600 $ENV_FILE." >&2
}

dry_run=false
confirm=false
args=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=true ;;
    --confirm) confirm=true ;;
    --*) usage "Unknown option: $arg"; exit 1 ;;
    *) args+=("$arg") ;;
  esac
done

if [ "${#args[@]}" -gt 1 ]; then
  usage "Too many arguments"
  exit 1
fi

if [ "${#args[@]}" -eq 1 ]; then
  message="${args[0]}"
elif [ ! -t 0 ]; then
  message="$(</dev/stdin)"
else
  usage "Too few arguments"
  exit 1
fi

if [[ ! "$message" =~ [^[:space:]] ]]; then
  usage "Message is empty"
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  usage "$ENV_FILE not found"
  exit 1
fi

env_mode="$(stat -c '%a' "$ENV_FILE")"
if [ "$env_mode" != "600" ]; then
  echo "$SCRIPT_NAME: $ENV_FILE must have mode 600; actual mode is $env_mode." >&2
  echo "Next: run chmod 600 $ENV_FILE and retry." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

for name in NTFY_SERVER NTFY_TOPIC NTFY_TITLE NTFY_PRIORITY; do
  if [ -z "${!name-}" ]; then
    echo "$SCRIPT_NAME: $name is missing or empty in $ENV_FILE." >&2
    echo "Next: edit $ENV_FILE and retry." >&2
    exit 1
  fi
done

if [[ ! "$NTFY_SERVER" =~ ^https://[^[:space:]/]+/?$ ]]; then
  echo "$SCRIPT_NAME: NTFY_SERVER must be an HTTPS origin without a path." >&2
  echo "Next: set NTFY_SERVER to a value such as https://ntfy.sh." >&2
  exit 1
fi
if [[ ! "$NTFY_TOPIC" =~ ^[A-Za-z0-9_-]{32,}$ ]]; then
  echo "$SCRIPT_NAME: NTFY_TOPIC must contain at least 32 letters, digits, underscores, or hyphens." >&2
  echo "Next: generate a topic with 'openssl rand -hex 24', write it to $ENV_FILE, and retry." >&2
  exit 1
fi
if [[ "$NTFY_TITLE" == *$'\n'* || "$NTFY_TITLE" == *$'\r'* ]]; then
  echo "$SCRIPT_NAME: NTFY_TITLE must be one line." >&2
  echo "Next: edit NTFY_TITLE in $ENV_FILE and retry." >&2
  exit 1
fi
case "$NTFY_PRIORITY" in
  min|low|default|high|max) ;;
  *)
    echo "$SCRIPT_NAME: NTFY_PRIORITY must be min, low, default, high, or max." >&2
    echo "Next: edit NTFY_PRIORITY in $ENV_FILE and retry." >&2
    exit 1
    ;;
esac

message_bytes="$(printf '%s' "$message" | wc -c)"
echo "Input: message_bytes=$message_bytes, server=$NTFY_SERVER, title=$NTFY_TITLE, priority=$NTFY_PRIORITY" >&2
echo "Output: one notification to the secret topic configured in $ENV_FILE" >&2

if "$dry_run"; then
  echo "$SCRIPT_NAME: Dry run completed; no notification was sent." >&2
  echo "Next: run without --dry-run to send the notification." >&2
  exit 0
fi

if "$confirm"; then
  if [ ! -r /dev/tty ]; then
    echo "$SCRIPT_NAME: --confirm requires an interactive terminal." >&2
    echo "Next: rerun from a terminal, or omit --confirm." >&2
    exit 1
  fi
  read -r -p "Send this notification? [y/N] " answer </dev/tty
  if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
    echo "$SCRIPT_NAME: Aborted; no notification was sent." >&2
    echo "Next: rerun when you are ready." >&2
    exit 1
  fi
fi

if curl \
  --request POST \
  --fail-with-body \
  --silent \
  --show-error \
  --retry 3 \
  --retry-delay 2 \
  --retry-all-errors \
  --connect-timeout 10 \
  --max-time 30 \
  --header "X-Title: $NTFY_TITLE" \
  --header "X-Priority: $NTFY_PRIORITY" \
  --data-binary "$message" \
  "${NTFY_SERVER%/}/$NTFY_TOPIC" \
  >/dev/null; then
  echo "$SCRIPT_NAME: Notification accepted by ntfy." >&2
  echo "Next: confirm that it arrived on the subscribed smartphone." >&2
else
  status=$?
  echo "$SCRIPT_NAME: Notification failed with curl exit code $status." >&2
  echo "Next: check the network, ntfy app subscription, and $ENV_FILE, then retry." >&2
  exit "$status"
fi
