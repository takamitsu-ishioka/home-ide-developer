#!/usr/bin/env bash
set -euo pipefail

SCRIPT=$(basename "$0")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 2 ]; then
  echo "$SCRIPT: Too few arguments" >&2
  echo "usage: $SCRIPT <year> <month>" >&2
  echo "example: $SCRIPT 2026 7" >&2
  exit 1
fi

ENV_FILE="${FREEE_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 "$SCRIPT_DIR/fetch_work_records.py" "$@"
