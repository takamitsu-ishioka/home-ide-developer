"""Implementation for claude_statusline.sh; do not run directly.

Claude Code statusLine hook: prints the "current repository" status-bar
text, and -- as a side effect -- caches this turn's rate_limits (5-hour /
7-day usage %, resets_at) to rate_limits_cache.json next to current_repo.
claude_rate_limit_report.sh reads that cache; this keeps OAuth credentials
entirely inside Claude Code's own process, never touched by scripts we write.
"""
import json
import sys
from datetime import datetime


def cache_rate_limits(status, cache_file):
    rate_limits = status.get("rate_limits")
    if not rate_limits:
        return  # not yet available this turn; leave any previous cache as-is
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "captured_at": datetime.now().astimezone().isoformat(),
                "rate_limits": rate_limits,
            },
            f,
            ensure_ascii=False,
        )


def repo_status_text(repo_file):
    try:
        with open(repo_file, encoding="utf-8") as f:
            return "repo: " + json.load(f).get("name", "?")
    except (FileNotFoundError, json.JSONDecodeError):
        return "repo: (none)"


def main():
    repo_file, cache_file = sys.argv[1], sys.argv[2]
    try:
        status = json.load(sys.stdin)
    except json.JSONDecodeError:
        status = {}

    cache_rate_limits(status, cache_file)
    print(repo_status_text(repo_file))


if __name__ == "__main__":
    main()
