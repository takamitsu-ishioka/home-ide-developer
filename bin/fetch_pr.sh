#!/bin/bash
# Fetch a GitHub PR's details via gh CLI.

SCRIPT_NAME=$(basename "$0")

cd "$(dirname "$0")"

function echo2() {
  echo -e "\033[1;34m$1\033[0m" >&2
}

function usage() {
  echo2 "$SCRIPT_NAME: $*"
  echo2 "Usage: $SCRIPT_NAME <owner> <repo> <pr_number>"
  echo2 "Example: $SCRIPT_NAME uenoyama-dominosoft fl-mmwave 393"
  exit 1
}

if [ "$#" -ne 3 ]; then
    usage "Invalid number of arguments"
fi

OWNER="$1"
REPO="$2"
PR_NUMBER="$3"

echo2 "Fetching PR #$PR_NUMBER from $OWNER/$REPO..."

python3 ./fetch_pr.py "$OWNER" "$REPO" "$PR_NUMBER"
