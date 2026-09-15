import base64
import json
import urllib.error
import urllib.request
from datetime import datetime

JIRA_BASE_URL = "https://dominosvr.atlassian.net"


class JiraApiError(Exception):
    """POST失敗時に送出する。メッセージ整形・exit方法は呼び出し元(各CLI)が決める。"""


def resolve_started(text: str) -> str:
    if text == "NOW":
        dt = datetime.now().astimezone()
    else:
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            raise JiraApiError(f"invalid started: {text} (expected NOW or YYYY-MM-DDTHH:MM)")
        dt = dt.astimezone()
    # Jira worklog API v2 が要求する形式: 2021-01-17T12:34:00.000+0900
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000%z")


def post_worklog(issue_key: str, started: str, seconds: int, comment: str, email: str, token: str) -> dict:
    """1件のworklogをJiraへPOSTする。startedはresolve_started()済みの文字列。"""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/worklog"
    body = {"comment": comment, "started": started, "timeSpentSeconds": seconds}
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        hint = " (JIRA_API_TOKENが無効・期限切れの可能性があります)" if e.code == 401 else ""
        raise JiraApiError(f"POST {url} failed: HTTP {e.code} {e.reason}: {body_text}{hint}")


def delete_worklog(issue_key: str, worklog_id: str, email: str, token: str) -> None:
    """1件のworklogをJiraから削除する。"""
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{issue_key}/worklog/{worklog_id}"
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
        },
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            return
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        hint = " (JIRA_API_TOKENが無効・期限切れの可能性があります)" if e.code == 401 else ""
        raise JiraApiError(f"DELETE {url} failed: HTTP {e.code} {e.reason}: {body_text}{hint}")
