#!/bin/bash
# List local git repositories found under <root_dir> (directories directly
# containing a .git entry), as tsv or json to stdout: path, name (from the
# "origin" remote's URL, falling back to the directory's own basename),
# branch, remote_url. Pure `git`, local filesystem only -- no GitHub or
# any other hosting API involved. See ~/bin/github/github_repos_list.sh
# for the GitHub-specific equivalent (repos that exist on GitHub, whether
# or not they're cloned here).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <root_dir> <tsv|json>"
    echo "example: $BASENAME ~ tsv > repos.tsv"
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 2 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

root_dir="$1"
format="$2"

if [ ! -d "$root_dir" ]; then
  usage "Not a directory: $root_dir"
  exit 1
fi

case "$format" in
  tsv|json) ;;
  *)
    usage "Unknown format '$format', expected tsv or json"
    exit 1
    ;;
esac

exec python3 "$SCRIPT_DIR/git_local_repos_list.py" "$root_dir" "$format"
