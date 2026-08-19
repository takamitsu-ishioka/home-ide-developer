#!/bin/bash
# Download the official Windows user installer for Visual Studio Code, update
# the existing installation without starting VS Code, and exit.
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
if [ "$version" != "latest" ] && [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  usage "Invalid version"
  exit 1
fi

cmd_path="$(wslpath -u 'C:\Windows\System32\cmd.exe')"
windows_root="$(wslpath -u 'C:\')"
if [ ! -x "$cmd_path" ]; then
  echo "$BASENAME: cmd.exe not found -- run this command inside WSL" >&2
  echo "$BASENAME: next action: enable WSL interop and retry" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "$BASENAME: curl not found" >&2
  echo "$BASENAME: next action: install curl and retry" >&2
  exit 1
fi

shopt -s nullglob
code_candidates=(
  "$windows_root/Program Files/Microsoft VS Code/bin/code"
  "$windows_root"/Users/*/AppData/Local/Programs/"Microsoft VS Code"/bin/code
)
shopt -u nullglob

code_path=""
for candidate in "${code_candidates[@]}"; do
  if [ -x "$candidate" ]; then
    code_path="$candidate"
    break
  fi
done

if [ -z "$code_path" ]; then
  echo "$BASENAME: installed VS Code not found" >&2
  echo "$BASENAME: next action: install VS Code once, then retry" >&2
  exit 1
fi

install_root="$(dirname "$(dirname "$code_path")")"
product_file="$(find "$install_root" -maxdepth 5 -type f -name product.json -print -quit)"
if [ -z "$product_file" ]; then
  echo "$BASENAME: product.json not found below: $install_root" >&2
  echo "$BASENAME: next action: check the VS Code installation and retry" >&2
  exit 1
fi

installed_commit="$(sed -n 's/^[[:space:]]*"commit":[[:space:]]*"\([0-9a-fA-F]*\)".*/\1/p' "$product_file" | head -1)"
if [[ ! "$installed_commit" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo "$BASENAME: cannot determine installed commit from: $product_file" >&2
  echo "$BASENAME: next action: check the commit field in product.json" >&2
  exit 1
fi

download_url="https://update.code.visualstudio.com/$version/win32-x64-user/stable"

if [ "$version" = "latest" ]; then
  check_url="https://update.code.visualstudio.com/api/update/win32-x64-user/stable/$installed_commit"
  if ! http_status="$(curl --silent --show-error --output /dev/null \
    --write-out '%{http_code}' "$check_url")"; then
    echo "$BASENAME: update check failed" >&2
    echo "$BASENAME: next action: check the network connection and retry" >&2
    exit 1
  fi

  case "$http_status" in
    204)
      echo "$BASENAME: VS Code is already up to date; download skipped" >&2
      echo "$BASENAME: next action: no action is required" >&2
      exit 0
      ;;
    200)
      echo "$BASENAME: VS Code update is available" >&2
      ;;
    *)
      echo "$BASENAME: update check returned HTTP $http_status" >&2
      echo "$BASENAME: next action: check the VS Code update service and retry" >&2
      exit 1
      ;;
  esac
fi

windows_temp="$(cd "$windows_root" && "$cmd_path" /d /c echo %TEMP% | tr -d '\r')"
temp_root="$(wslpath -u "$windows_temp")"
if [ ! -d "$temp_root" ]; then
  echo "$BASENAME: Windows temporary directory not found: $temp_root" >&2
  echo "$BASENAME: next action: check WSL interop and retry" >&2
  exit 1
fi

temp_dir="$(mktemp -d "$temp_root/vscode_update.XXXXXX")"
installer_path="$temp_dir/VSCodeUserSetup-x64.exe"

cleanup() {
  if [ -d "$temp_dir" ] && [ ! -L "$temp_dir" ] && [[ "$temp_dir" == "$temp_root"/vscode_update.* ]]; then
    rm -f "$installer_path"
    rmdir "$temp_dir"
  fi
}
trap cleanup EXIT

echo "$BASENAME: input version: $version" >&2
echo "$BASENAME: output: updated Windows VS Code installation" >&2
echo "$BASENAME: download: $download_url" >&2

curl --fail --location --progress-bar --output "$installer_path" "$download_url"

(
  cd "$windows_root"
  "$installer_path" /SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART \
    /NOCLOSEAPPLICATIONS /MERGETASKS=!runcode
)

echo "$BASENAME: VS Code update completed" >&2
echo "$BASENAME: next action: run vscode.sh to start VS Code" >&2
