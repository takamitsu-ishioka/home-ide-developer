#!/bin/bash
# List GitHub repositories that are candidates for "created by me": every
# non-fork repo under the logged-in gh user's own account, plus every repo
# the user can administer (viewerCanAdminister) in each org they belong to
# (orgs auto-discovered via `gh api user/orgs`).
#
# GitHub's API has no "repository creator" field for org-owned repos, so
# whether an org repo is actually the user's own work is looked up in
# config.json (hand-maintained allowlist) instead of guessed.
#
# Output columns (tsv) / fields (json): name_with_owner, created_by_me
# (yes/no), visibility, created_at, pushed_at, description, url. Personal-
# account repos are always created_by_me=yes (owner==creator, forks
# already excluded). Org repos default to created_by_me=no unless listed
# in config.json.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <tsv|json>"
    echo "example: $BASENAME tsv > repos.tsv"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

case "$1" in
  tsv|json) ;;
  *)
    usage "Unknown format '$1', expected tsv or json"
    exit 1
    ;;
esac

exec python3 "$SCRIPT_DIR/github_repos_list.py" "$1"
