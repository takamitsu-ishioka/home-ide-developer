#!/bin/bash
# Report orientation for the current shell: which environment
# (LOCAL/ALPHA/BETA/PROD, from ~/environment_name), hostname, current
# directory, and -- if inside one -- git repo/branch/remote. Named after
# `whoami`, for the same reason: a quick "where am I right now" check
# before running anything environment-specific.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <json|tsv>"
    echo "example: $BASENAME json"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

case "$1" in
  json|tsv) ;;
  *)
    usage "Unknown format '$1', expected json or tsv"
    exit 1
    ;;
esac

exec python3 "$SCRIPT_DIR/whereami.py" "$1"
