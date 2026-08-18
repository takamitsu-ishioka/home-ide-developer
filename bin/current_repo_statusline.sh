#!/bin/bash
# Claude Code statusLine: display the "current repository" (persisted at
# <repo_local_dir.sh>/current_repo, see current_repo_set.sh). Also caches
# this turn's rate_limits (5-hour/weekly usage %) to rate_limits_cache.json
# next to it, for claude_rate_limit_report.sh to read on demand -- this
# keeps OAuth credentials entirely inside Claude Code, never touched here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(repo_local_dir.sh 2>/dev/null || true)"

python3 "$SCRIPT_DIR/current_repo_statusline.py" "${repo_dir}/current_repo" "${repo_dir}/rate_limits_cache.json"
