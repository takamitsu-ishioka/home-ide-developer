#!/usr/bin/env python3
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict:
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def build_description(github_url: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "作業内容"}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "inlineCard", "attrs": {"url": github_url}},
                    {"type": "text", "text": " "},
                ],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "完了条件"}],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "PR closed"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "issue closed"}],
                            }
                        ],
                    },
                ],
            },
        ],
    }


def create_ticket(env: dict, ticket: dict) -> dict:
    base_url = env["JIRA_BASE_URL"].rstrip("/")
    credentials = base64.b64encode(
        f"{env['JIRA_EMAIL']}:{env['JIRA_TOKEN']}".encode()
    ).decode()

    payload = {
        "fields": {
            "project": {"key": env["JIRA_PROJECT_KEY"]},
            "summary": ticket["summary"],
            "issuetype": {"id": ticket["issuetype_id"]},
            "assignee": {
                "accountId": ticket.get(
                    "assignee_account_id", env["JIRA_ASSIGNEE_ACCOUNT_ID"]
                )
            },
            "customfield_10049": env["JIRA_CONTRACT_ID"],
            "description": build_description(ticket["github_issue_url"]),
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/rest/api/3/issue",
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def usage():
    name = Path(__file__).name
    print(f"{name}: Too few arguments", file=sys.stderr)
    print(f"usage: {name}", file=sys.stderr)
    print(f"example: {name} < ticket.jsonc", file=sys.stderr)
    sys.exit(1)


def main():
    if sys.stdin.isatty():
        usage()

    env_path_candidates = [
        Path(
            __import__("os").environ.get(
                "JIRA_ENV_FILE",
                Path(__file__).parent / ".env",
            )
        ),
    ]
    env_path = next((p for p in env_path_candidates if p.exists()), None)
    if env_path is None:
        print(
            f"Error: .env not found. Place it at {Path(__file__).parent / '.env'} "
            "or set JIRA_ENV_FILE.",
            file=sys.stderr,
        )
        sys.exit(1)

    env = load_env(env_path)
    for key in (
        "JIRA_EMAIL",
        "JIRA_TOKEN",
        "JIRA_BASE_URL",
        "JIRA_PROJECT_KEY",
        "JIRA_CONTRACT_ID",
        "JIRA_ASSIGNEE_ACCOUNT_ID",
    ):
        if key not in env:
            print(f"Error: {key} is missing in {env_path}", file=sys.stderr)
            sys.exit(1)

    try:
        lines = [l for l in sys.stdin if not l.lstrip().startswith("//")]
        ticket = json.loads("".join(lines))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    for key in ("summary", "github_issue_url", "issuetype_id"):
        if key not in ticket:
            print(f"Error: '{key}' is required in JSON input", file=sys.stderr)
            sys.exit(1)

    placeholders = ["タイトル", "#000", "/issues/000"]
    for ph in placeholders:
        for key in ("summary", "github_issue_url"):
            if ph in ticket.get(key, ""):
                print(f"Error: '{key}' contains placeholder '{ph}'. Edit the template before running.", file=sys.stderr)
                sys.exit(1)

    try:
        result = create_ticket(env, ticket)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    key = result["key"]
    base_url = env["JIRA_BASE_URL"].rstrip("/")
    print(f"{key}: {base_url}/browse/{key}")


if __name__ == "__main__":
    main()
