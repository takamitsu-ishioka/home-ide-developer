#!/bin/bash
# Keep the ~/.<repo-name> marker directory (identified by the sentinel
# file .repo-name-marker inside it, since its name is exactly what may
# change) in sync with the actual GitHub repo name, read from the
# "origin" remote. Exists because this repo is cloned at ~/, whose
# basename is the Linux username "developer", not the repo's real name --
# an incidental mismatch that has caused real bugs (see
# ~/.home-ide-developer/README.md). Run automatically via a SessionStart
# hook; safe to run any number of times (idempotent), and silent when
# nothing has changed. If there's no "origin" remote, does nothing and
# exits 0 -- that's expected outside a configured clone, not an error.
set -uo pipefail

BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME"
    echo "example: $BASENAME"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 0 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

remote_url="$(git -C "$HOME" remote get-url origin 2>/dev/null)"
if [ -z "$remote_url" ]; then
  exit 0
fi

name="$(basename "$remote_url")"
name="${name%.git}"
target="$HOME/.$name"
sentinel=".repo-name-marker"

if [ -d "$target" ] && [ -f "$target/$sentinel" ]; then
  exit 0
fi

current="$(find "$HOME" -maxdepth 2 -type f -name "$sentinel" 2>/dev/null | head -1)"
if [ -n "$current" ]; then
  current_dir="$(dirname "$current")"
  if [ "$current_dir" != "$target" ]; then
    mv "$current_dir" "$target"
    echo "$BASENAME: renamed $(basename "$current_dir") -> $(basename "$target") (repo name changed)" >&2
  fi
else
  mkdir -p "$target"
  touch "$target/$sentinel"
  echo "$BASENAME: created $target" >&2
fi
