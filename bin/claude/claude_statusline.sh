#!/bin/bash
# NOT for direct/manual use -- this is a Claude Code hook, invoked
# automatically by the `claude` app itself. Wired up as the `statusLine`
# command in ~/.claude/settings.json; never run standalone.
#
# Role: renders the status-bar text, showing the "current repository"
# (persisted at <repo_local_dir.sh>/current_repo, see current_repo_set.sh).
# Also caches this turn's rate_limits (5-hour/weekly usage %) to
# rate_limits_cache.json next to it, for claude_rate_limit_report.sh to
# read on demand -- this keeps OAuth credentials entirely inside Claude
# Code's own process, never touched by that (or this) script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(repo_local_dir.sh 2>/dev/null || true)"

python3 "$SCRIPT_DIR/claude_statusline.py" "${repo_dir}/current_repo" "${repo_dir}/rate_limits_cache.json"
