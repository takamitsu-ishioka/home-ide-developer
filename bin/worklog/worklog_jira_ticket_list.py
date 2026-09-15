import json
import os
import sys

import worklog_jira_api
import worklog_jira_query

PROG = os.path.basename(__file__)
JQL = "assignee = currentUser() AND statusCategory != Done ORDER BY status ASC, updated DESC"


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"{name} is not set")
    return value


def fetch_my_tickets(email: str, token: str) -> list[dict]:
    """自分にアサインされ、statusCategoryがDoneでない(backlog/進行中)チケットを取得する。"""
    body = {"jql": JQL, "fields": ["key", "status", "summary"], "maxResults": 50}
    issues = []
    while True:
        data = worklog_jira_query.api_post("/rest/api/3/search/jql", email, token, body)
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issues.append(
                {
                    "key": issue["key"],
                    "status": (fields.get("status") or {}).get("name", ""),
                    "summary": fields.get("summary", ""),
                    "url": f"{worklog_jira_api.JIRA_BASE_URL}/browse/{issue['key']}",
                }
            )
        if data.get("isLast", True) or not data.get("nextPageToken"):
            break
        body["nextPageToken"] = data["nextPageToken"]
    return issues


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 1 or args[0] not in ("tsv", "json"):
        fail(f"usage: {PROG} <tsv|json>")
    output_format = args[0]

    email = require_env("JIRA_EMAIL")
    token = require_env("JIRA_API_TOKEN")

    try:
        issues = fetch_my_tickets(email, token)
    except worklog_jira_api.JiraApiError as e:
        fail(str(e))

    if output_format == "json":
        print(json.dumps(issues, ensure_ascii=False))
    else:
        for issue in issues:
            print(f"{issue['key']}\t{issue['status']}\t{issue['summary']}\t{issue['url']}")
    print(f"{PROG}: {len(issues)}件", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
