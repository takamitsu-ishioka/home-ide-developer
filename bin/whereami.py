"""Report orientation: which environment/host/git context this shell is in.

Called only from whereami.sh (see docs/CLAUDE.md scripting rules: python is
always a thin-wrapped implementation, never run standalone).

Fields: environment (LOCAL/ALPHA/BETA/PROD, from ~/environment_name --
untracked, machine-local, see environment_name.template), hostname, cwd,
git_repo, git_branch, git_remote. Any field whose source is unavailable
(no marker file, not inside a git repo, no "origin" remote) is empty/null
rather than guessed.
"""
import json
import re
import socket
import subprocess
import sys
from pathlib import Path


def read_environment_name() -> str:
    path = Path.home() / "environment_name"
    if not path.exists():
        return ""
    return path.read_text().strip()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=Path.cwd()
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def repo_name(remote_url: str, git_toplevel: str) -> str:
    # The remote's own name for the repo is the source of truth -- the
    # local checkout directory's basename need not match it (e.g. this
    # repo is cloned at ~/, whose basename is the Linux username
    # "developer", not the GitHub repo name "home-ide-developer").
    if remote_url:
        return re.sub(r"\.git$", "", remote_url.rsplit("/", 1)[-1])
    return Path(git_toplevel).name


def collect() -> dict:
    git_toplevel = git("rev-parse", "--show-toplevel")
    git_remote = git("remote", "get-url", "origin") if git_toplevel else ""
    return {
        "environment": read_environment_name(),
        "hostname": socket.gethostname(),
        "cwd": str(Path.cwd()),
        "git_repo": repo_name(git_remote, git_toplevel) if git_toplevel else "",
        "git_branch": git("rev-parse", "--abbrev-ref", "HEAD") if git_toplevel else "",
        "git_remote": git_remote,
    }


def main() -> None:
    format_ = sys.argv[1]
    info = collect()

    if format_ == "tsv":
        print(
            "\t".join(
                info[k]
                for k in ("environment", "hostname", "cwd", "git_repo", "git_branch", "git_remote")
            )
        )
    else:
        print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
