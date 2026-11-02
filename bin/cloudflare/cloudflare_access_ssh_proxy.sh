#!/usr/bin/env bash
# ssh ProxyCommand for hosts behind Cloudflare Access (cloudflared access ssh).
# Authenticates with the Access service token in the .env next to this script,
# so no browser login or email PIN is needed. Without .env it falls back to the
# browser login (24-hour session).
# stdout carries the SSH stream; every message goes to stderr.
# In ~/.ssh/config:
#   ProxyCommand ~/bin/cloudflare/cloudflare_access_ssh_proxy.sh %h
set -euo pipefail

SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

usage() {
  echo "$SCRIPT_NAME: $1" >&2
  echo "usage: $SCRIPT_NAME <hostname>" >&2
  echo "example: $SCRIPT_NAME office-ssh-ishioka.domino8.net" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/, ""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
}

if [ "$#" -lt 1 ]; then
  usage "Too few arguments"
  exit 1
fi
if [ "$#" -gt 1 ]; then
  usage "Too many arguments"
  exit 1
fi
hostname="$1"

if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT_NAME: $ENV_FILE not found; falling back to browser login." >&2
  echo "Next: copy $SCRIPT_DIR/.env.template to $ENV_FILE, fill in the service token, and run chmod 600 $ENV_FILE." >&2
  exec cloudflared access ssh --hostname "$hostname"
fi

env_mode="$(stat -c '%a' "$ENV_FILE")"
if [ "$env_mode" != "600" ]; then
  echo "$SCRIPT_NAME: $ENV_FILE must have mode 600; actual mode is $env_mode." >&2
  echo "Next: run chmod 600 $ENV_FILE and retry." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

for name in CF_ACCESS_CLIENT_ID CF_ACCESS_CLIENT_SECRET; do
  if [ -z "${!name-}" ]; then
    echo "$SCRIPT_NAME: $name is missing or empty in $ENV_FILE." >&2
    echo "Next: edit $ENV_FILE and retry." >&2
    exit 1
  fi
done

# Hand the token to cloudflared through its own environment variables, not
# --id/--secret, so the secret does not show up in ps output.
TUNNEL_SERVICE_TOKEN_ID="$CF_ACCESS_CLIENT_ID" \
TUNNEL_SERVICE_TOKEN_SECRET="$CF_ACCESS_CLIENT_SECRET" \
  exec cloudflared access ssh --hostname "$hostname"
