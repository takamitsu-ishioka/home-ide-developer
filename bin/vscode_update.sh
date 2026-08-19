#!/bin/bash
# Update the Windows installation of Visual Studio Code from WSL and exit.
# The required version is either "latest" or an explicit package version.
set -euo pipefail

BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <latest|version>"
    echo "example: $BASENAME latest"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

version="$1"
if [[ "$version" == -* ]] || [ -z "$version" ]; then
  usage "Invalid version"
  exit 1
fi

cmd_path="$(wslpath -u 'C:\Windows\System32\cmd.exe')"
if [ ! -x "$cmd_path" ]; then
  echo "$BASENAME: cmd.exe not found -- run this command inside WSL" >&2
  echo "$BASENAME: next action: enable WSL interop and retry" >&2
  exit 1
fi

echo "$BASENAME: input version: $version" >&2
echo "$BASENAME: output: updated Windows VS Code installation" >&2

if [ "$version" = "latest" ]; then
  "$cmd_path" /d /c winget upgrade --id Microsoft.VisualStudioCode --exact --silent \
    --accept-source-agreements --accept-package-agreements
else
  "$cmd_path" /d /c winget upgrade --id Microsoft.VisualStudioCode --exact --version "$version" --silent \
    --accept-source-agreements --accept-package-agreements
fi

echo "$BASENAME: VS Code update completed" >&2
echo "$BASENAME: next action: run vscode.sh to start VS Code" >&2
