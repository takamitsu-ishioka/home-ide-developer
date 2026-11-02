#!/usr/bin/env bash
# Count the INBOX messages of each given user on www.starship.jp and send one
# ntfy notification when any user has more than <threshold> messages.
# The notification carries the command line that deletes old mail, so nobody
# has to remember starship_mail_old_delete.sh. Meant to run daily from cron.
# Prints "user<TAB>count" for every user to stdout.
set -euo pipefail

SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSH_HOST="starship-jp"
MAILBOX="INBOX"
NTFY_SEND="$SCRIPT_DIR/../ntfy/ntfy_notification_send.sh"
DELETE_CMD="~/bin/starship_jp/starship_mail_old_delete.sh"

usage() {
  echo "$SCRIPT_NAME: $1" >&2
  echo "usage: $SCRIPT_NAME <threshold> <user> [<user>...] [--dry-run]" >&2
  echo "example: $SCRIPT_NAME 500 ishioka information kisaburo --dry-run" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/, ""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
}

dry_run=false
args=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=true ;;
    --*) usage "Unknown option: $arg"; exit 1 ;;
    *) args+=("$arg") ;;
  esac
done

if [ "${#args[@]}" -lt 2 ]; then
  usage "Too few arguments"
  exit 1
fi

threshold="${args[0]}"
users=("${args[@]:1}")

if [[ ! "$threshold" =~ ^[1-9][0-9]*$ ]]; then
  usage "<threshold> must be a positive integer: $threshold"
  exit 1
fi
for user in "${users[@]}"; do
  if [[ ! "$user" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
    usage "Invalid user: $user"
    exit 1
  fi
done

echo "Host:      $SSH_HOST" >&2
echo "Users:     ${users[*]}" >&2
echo "Threshold: more than $threshold messages in $MAILBOX" >&2
echo "Notify:    $NTFY_SEND$([ "$dry_run" = true ] && echo ' (dry run: not sent)')" >&2

remote_script=""
for user in "${users[@]}"; do
  remote_script+="printf '%s\t%s\n' $user \"\$(sudo doveadm search -u $user mailbox $MAILBOX all | wc -l)\"; "
done

if ! counts="$(ssh -o BatchMode=yes -o ConnectTimeout=15 "$SSH_HOST" "$remote_script")"; then
  echo "$SCRIPT_NAME: Could not count messages on $SSH_HOST." >&2
  echo "Next: check ssh $SSH_HOST and that every user exists (sudo doveadm user '*')." >&2
  exit 1
fi
printf '%s\n' "$counts"

over=""
while IFS=$'\t' read -r user count; do
  if [ "$count" -gt "$threshold" ]; then
    over+="$user: $count 通"$'\n'"  $DELETE_CMD $user 30 --dry-run"$'\n'
  fi
done <<<"$counts"

if [ -z "$over" ]; then
  echo "$SCRIPT_NAME: Every mailbox has $threshold messages or fewer." >&2
  echo "Next: nothing to do." >&2
  exit 0
fi

message="starship.jp のメールが $threshold 通を超えています。"$'\n'"$over"
message+="確認後、--dry-run を外すと削除します。imc に取り込まれていないユーザーのメールは、消すとどこにも残りません。"

if [ "$dry_run" = true ]; then
  printf '%s\n' "$message" >&2
  echo "$SCRIPT_NAME: Dry run completed; no notification was sent." >&2
  echo "Next: rerun without --dry-run to send it." >&2
  exit 0
fi

printf '%s\n' "$message" | "$NTFY_SEND"
echo "$SCRIPT_NAME: Notification sent." >&2
echo "Next: run the command line in the notification." >&2
