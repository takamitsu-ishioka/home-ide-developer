#!/usr/bin/env bash
# Delete old mail from one user's INBOX on www.starship.jp (Dovecot, via doveadm).
# A message is old when it was received more than <days> days ago (internal date;
# doveadm "savedbefore" is not used because IMAP access can reset the saved date).
# Connects with the ssh alias starship-jp and runs doveadm through sudo.
# Mail that imc has already fetched stays in imc, because imc's mbsync uses
# "Expunge None"; run imc_fetch.sh mail first if imc should keep a copy.
set -euo pipefail

SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
SSH_HOST="starship-jp"
MAILBOX="INBOX"

usage() {
  echo "$SCRIPT_NAME: $1" >&2
  echo "usage: $SCRIPT_NAME <user> <days> [--dry-run] [--confirm]" >&2
  echo "example: $SCRIPT_NAME ishioka 30 --dry-run" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/, ""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
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

if [ "${#args[@]}" -lt 2 ]; then
  usage "Too few arguments"
  exit 1
fi
if [ "${#args[@]}" -gt 2 ]; then
  usage "Too many arguments"
  exit 1
fi

user="${args[0]}"
days="${args[1]}"

if [[ ! "$user" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
  usage "Invalid user: $user"
  exit 1
fi
if [[ ! "$days" =~ ^[1-9][0-9]*$ ]]; then
  usage "<days> must be a positive integer: $days"
  exit 1
fi

query="mailbox $MAILBOX before ${days}d"

remote() {
  ssh -o BatchMode=yes -o ConnectTimeout=15 "$SSH_HOST" "$1"
}

if ! total="$(remote "sudo doveadm search -u $user mailbox $MAILBOX all | wc -l")"; then
  echo "$SCRIPT_NAME: Could not query $user on $SSH_HOST." >&2
  echo "Next: check ssh $SSH_HOST and that $user exists (sudo doveadm user '*')." >&2
  exit 1
fi
old="$(remote "sudo doveadm search -u $user $query | wc -l")"

echo "Host:     $SSH_HOST" >&2
echo "User:     $user" >&2
echo "Query:    $query" >&2
echo "Messages: $total in $MAILBOX, $old to delete, $((total - old)) to keep" >&2

if [ "$old" -eq 0 ]; then
  echo "$SCRIPT_NAME: Nothing to delete." >&2
  echo "Next: use a smaller <days> if the mailbox is still too large." >&2
  exit 0
fi

if [ "$dry_run" = true ]; then
  echo "$SCRIPT_NAME: Dry run completed; nothing was deleted." >&2
  echo "Next: rerun without --dry-run to delete $old messages." >&2
  exit 0
fi

if [ "$confirm" = true ]; then
  read -r -p "Delete $old messages from $user's $MAILBOX? [y/N] " answer </dev/tty
  if [ "$answer" != "y" ]; then
    echo "$SCRIPT_NAME: Aborted; nothing was deleted." >&2
    exit 1
  fi
fi

remote "sudo doveadm expunge -u $user $query"
after="$(remote "sudo doveadm search -u $user mailbox $MAILBOX all | wc -l")"

echo "$SCRIPT_NAME: Deleted $((total - after)) messages; $after remain in $user's $MAILBOX." >&2
echo "Next: let the mail client (Denshin8) resync; if mail piles up again, check whether it is set to leave mail on the server." >&2
