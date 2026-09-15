#!/usr/bin/env bash
# 指定したJQLにマッチする全issueのsummary+descriptionからキーワードのdocument frequency
# (そのキーワードを含むissueの件数)を集計し、bin/worklog/_ticket_corpus.sqlite3を
# 再構築する(既存の内容は毎回全置き換え)。worklog_guess_ticket_rules_update_suggest.shが
# 「単語の特異度(IDF)」を計算するために使う二次データ(_接頭辞、.gitignore対象)。
set -euo pipefail

SCRIPT=$(basename "${BASH_SOURCE[0]}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

args=()
for a in "$@"; do
  [ "$a" = "--dry-run" ] || [ "$a" = "--confirm" ] || args+=("$a")
done

if [ "${#args[@]}" -ne 1 ]; then
  echo "$SCRIPT: Invalid arguments" >&2
  echo "usage: $SCRIPT <jql> [--dry-run] [--confirm]" >&2
  echo "  jql: 集計対象issueを絞り込むJQL" >&2
  echo "example: $SCRIPT 'project in (MMWAVE, GENERAL)' --confirm" >&2
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "${BASH_SOURCE[0]}" >&2
  exit 1
fi

ENV_FILE="${WORKLOG_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 "$SCRIPT_DIR/worklog_ticket_corpus_build.py" "$@"
