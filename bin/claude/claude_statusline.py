"""Implementation for claude_statusline.sh; do not run directly.

Claude Code statusLine hook: prints the repository of the session's working
directory (name = basename of the git top-level directory, plus branch) as
status-bar text, and -- as a side effect -- caches this turn's rate_limits
(5-hour / 7-day usage %, resets_at) to the given cache file.
claude_rate_limit_report.sh reads that cache; this keeps OAuth credentials
entirely inside Claude Code's own process, never touched by scripts we write.
"""
import json
import os
import subprocess
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


def git_output(cwd, *args):
    result = subprocess.run(
        ["git", "-C", cwd, *args], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def repo_status_text(cwd):
    # git has no notion of a repository name; the top-level directory name is
    # used uniformly, whether or not a remote exists.
    top_level = git_output(cwd, "rev-parse", "--show-toplevel")
    if not top_level:
        return "repo: (none)"
    branch = git_output(cwd, "branch", "--show-current") or "(detached)"
    return "repo: " + os.path.basename(top_level) + " (" + branch + ")"


def main():
    cache_file = sys.argv[1]
    try:
        status = json.load(sys.stdin)
    except json.JSONDecodeError:
        status = {}

    cache_rate_limits(status, cache_file)
    cwd = status.get("workspace", {}).get("current_dir") or os.getcwd()
    print(repo_status_text(cwd))


if __name__ == "__main__":
    main()
