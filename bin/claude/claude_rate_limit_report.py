"""Implementation for claude_rate_limit_report.sh; do not run directly.

Reports this machine's 5-hour/weekly Claude.ai rate-limit usage, read from
the cache that claude_statusline.sh (this session's Claude Code
statusLine hook) writes on every turn where Claude Code includes
rate_limits in its status JSON. No network calls and no OAuth credentials
are touched here -- Claude Code's own already-authenticated process is the
only thing that ever talks to the account-usage API.
"""
import json
import subprocess
import sys
from datetime import datetime


def fail(message):
    print(f"claude_rate_limit_report.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def repo_local_dir():
    result = subprocess.run(["repo_local_dir.sh"], capture_output=True, text=True)
    if result.returncode != 0:
        fail("could not resolve the repo-local data directory (repo_local_dir.sh failed)")
    return result.stdout.strip()


def format_window(window):
    if not window:
        return None
    resets_at = window.get("resets_at")
    return {
        "used_percentage": window.get("used_percentage"),
        "resets_at": (
            datetime.fromtimestamp(resets_at).astimezone().isoformat()
            if resets_at is not None
            else None
        ),
    }


def main():
    if len(sys.argv) != 1:
        fail("expected no arguments")

    cache_file = f"{repo_local_dir()}/rate_limits_cache.json"
    try:
        with open(cache_file, encoding="utf-8") as f:
            cache = json.load(f)
    except FileNotFoundError:
        fail(
            "no rate_limits cache yet -- send Claude Code any message in an "
            "active session first (the statusLine hook populates this after "
            "the first API response), then retry"
        )
    except json.JSONDecodeError:
        fail(f"cache file is not valid JSON: {cache_file}")

    rate_limits = cache.get("rate_limits", {})
    print(
        json.dumps(
            {
                "captured_at": cache.get("captured_at"),
                "five_hour": format_window(rate_limits.get("five_hour")),
                "seven_day": format_window(rate_limits.get("seven_day")),
                "note": (
                    "From the local cache written by this machine's "
                    "statusLine hook (claude_statusline.sh), not a "
                    "live API call -- reflects usage as of captured_at, "
                    "which updates automatically after each turn in any "
                    "active Claude Code session on this machine."
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        import os

        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
    finally:
        try:
            sys.stdout.close()
        except BrokenPipeError:
            pass
