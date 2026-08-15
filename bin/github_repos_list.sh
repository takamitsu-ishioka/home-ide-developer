#!/bin/bash
# List GitHub repositories owned (created) by the logged-in gh user.
# Forks are excluded (gh repo list --source), since a fork isn't a
# repository the user created.
# tsv: name_with_owner, visibility, created_at, pushed_at, description, url
# json: gh's native JSON array for the same fields
# Both are in whatever order gh returns (observed: pushed_at descending;
# gh repo list has no --sort flag to control or guarantee this).
set -euo pipefail

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

format="$1"
case "$format" in
  tsv|json) ;;
  *)
    usage "Unknown format '$format', expected tsv or json"
    exit 1
    ;;
esac

now() {
  TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S(JST)'
}

owner="$(gh api user --jq .login)"

echo "$(now) ${BASENAME}: listing repositories owned by ${owner} (${format})..." >&2

tmp_out="$(mktemp)"
trap 'rm -f "$tmp_out"' EXIT

if [ "$format" = "tsv" ]; then
  gh repo list "$owner" --source --no-archived -L 1000 \
    --json nameWithOwner,visibility,createdAt,pushedAt,description,url \
    -t '{{range .}}{{.nameWithOwner}}	{{.visibility}}	{{.createdAt}}	{{.pushedAt}}	{{.description}}	{{.url}}
{{end}}' > "$tmp_out"
  count=$(wc -l < "$tmp_out")
else
  gh repo list "$owner" --source --no-archived -L 1000 \
    --json nameWithOwner,visibility,createdAt,pushedAt,description,url \
    > "$tmp_out"
  count=$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' < "$tmp_out")
fi

cat "$tmp_out"
echo "$(now) ${BASENAME}: done, ${count} repositories." >&2
