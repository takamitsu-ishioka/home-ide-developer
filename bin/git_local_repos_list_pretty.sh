#!/bin/bash
# Combine git_local_repos_list.sh and json_pretty_print.sh: list local git
# repositories under <root_dir> as pretty-printed JSON.
#
# Exists because a Claude Code skill's `!`command`` substitution does not
# reliably run a piped command (cmd1 | cmd2) end-to-end -- observed:
# output sometimes silently fell back to just the first command's raw,
# compact output (undocumented behavior, not confirmed root-caused).
# Wrapping the pipe in one script sidesteps the ambiguity entirely.
set -euo pipefail

BASENAME="$(basename "$0")"

usage() {
  {
    echo "$BASENAME: $1"
    echo "usage: $BASENAME <root_dir>"
    echo "example: $BASENAME ."
    echo
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1{exit}' "$0"
  } >&2
}

if [ "$#" -ne 1 ]; then
  usage "Wrong number of arguments"
  exit 1
fi

git_local_repos_list.sh "$1" json | json_pretty_print.sh
