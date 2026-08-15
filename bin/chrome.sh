#!/bin/bash
# Open a URL in Windows Chrome from WSL, via cmd.exe's `start` (not
# PowerShell -- CLAUDE.md says avoid Windows-specific tools where possible,
# and cmd.exe is sufficient here). If Chrome is already running, this opens
# a new tab in the existing process instead of starting a second one --
# that's just what `start chrome <url>` does, no special flag needed.
set -euo pipefail

BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <url>"
    echo "example: $BASENAME https://example.com"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

url="$1"

if ! command -v cmd.exe >/dev/null 2>&1; then
  echo "$BASENAME: cmd.exe not found -- this only works inside WSL with interop enabled" >&2
  exit 1
fi

cmd.exe /c start chrome "$url" >/dev/null 2>&1
echo "$BASENAME: opened $url in Chrome" >&2
