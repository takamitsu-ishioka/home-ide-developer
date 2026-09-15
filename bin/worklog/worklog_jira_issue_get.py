import base64
import json
import os
import sys
import urllib.error
import urllib.request

JIRA_BASE_URL = "https://dominosvr.atlassian.net"
PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def api_get(url: str, email: str, token: str) -> object:
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        hint = " (JIRA_API_TOKENが無効・期限切れの可能性があります)" if e.code == 401 else ""
        fail(f"GET {url} failed: HTTP {e.code} {e.reason}: {body_text}{hint}")


def main() -> int:
    if len(sys.argv) != 2:
        fail(f"usage: {PROG} <issue_key>")
    issue_key = sys.argv[1]

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    print(f"{PROG}: {issue_key} のフィールドとremote linkを取得します", file=sys.stderr)
    issue = api_get(f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}", email, token)
    remote_links = api_get(f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/remotelink", email, token)

    out = {"issue": issue, "remote_links": remote_links}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
