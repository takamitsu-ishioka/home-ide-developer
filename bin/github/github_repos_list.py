"""List GitHub repositories that are candidates for "created by me".

Called only from github_repos_list.sh (see docs/CLAUDE.md scripting rules: python
is always a thin-wrapped implementation, never run standalone).

Combines two sources:
- every non-fork repo under the logged-in gh user's own account
  (owner == creator there, unambiguous)
- every repo the user can administer (viewerCanAdminister) in each org
  they belong to (orgs auto-discovered via `gh api user/orgs`)

GitHub's API has no "repository creator" field for org-owned repos, so
whether an org repo is actually the user's own work is looked up in
config.json (hand-maintained allowlist) instead of guessed.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
FIELDS = "nameWithOwner,visibility,createdAt,pushedAt,description,url"


def log(message: str) -> None:
    timestamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S(JST)")
    print(f"{timestamp} {message}", file=sys.stderr)


def run_gh_json(args: list[str]):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        log(f"gh {' '.join(args)} failed: {result.stderr.strip() or '(no stderr)'}")
        sys.exit(result.returncode)
    return json.loads(result.stdout)


def own_repos(login: str) -> list[dict]:
    repos = run_gh_json(
        ["repo", "list", login, "--source", "--no-archived", "-L", "1000", "--json", FIELDS]
    )
    for r in repos:
        r["createdByMe"] = True
    return repos


def org_repos(org: str, allowlist: set[str]) -> list[dict]:
    repos = run_gh_json(
        [
            "repo", "list", org, "--source", "--no-archived", "-L", "1000",
            "--json", f"{FIELDS},viewerCanAdminister",
        ]
    )
    admin_repos = [r for r in repos if r.pop("viewerCanAdminister")]
    for r in admin_repos:
        name = r["nameWithOwner"].split("/", 1)[1]
        r["createdByMe"] = name in allowlist
    return admin_repos


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text())


def print_tsv(repos: list[dict]) -> None:
    for r in repos:
        fields = [
            r["nameWithOwner"],
            "yes" if r["createdByMe"] else "no",
            r["visibility"],
            r["createdAt"],
            r["pushedAt"],
            r.get("description") or "",
            r["url"],
        ]
        print("\t".join(fields))


def main() -> None:
    format_ = sys.argv[1]
    config = load_config()

    login = run_gh_json(["api", "user"])["login"]
    log(f"listing repositories owned by {login}...")
    repos = own_repos(login)

    for org in run_gh_json(["api", "user/orgs"]):
        org_login = org["login"]
        allowlist = set(config.get(org_login, {}).get("created_by_me", []))
        log(f"listing repositories administered in {org_login}...")
        repos.extend(org_repos(org_login, allowlist))

    if format_ == "tsv":
        print_tsv(repos)
    else:
        print(json.dumps(repos, ensure_ascii=False))

    created_by_me = sum(r["createdByMe"] for r in repos)
    log(f"done, {len(repos)} repositories ({created_by_me} created by me).")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
