import base64
import json
import urllib.error
import urllib.request
from datetime import date, datetime

import worklog_jira_api

JIRA_BASE_URL = worklog_jira_api.JIRA_BASE_URL
JiraApiError = worklog_jira_api.JiraApiError


def api_get(path: str, email: str, token: str) -> dict:
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        f"{JIRA_BASE_URL}{path}",
        headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        hint = " (JIRA_API_TOKENが無効・期限切れの可能性があります)" if e.code == 401 else ""
        raise JiraApiError(f"GET {JIRA_BASE_URL}{path} failed: HTTP {e.code} {e.reason}: {body}{hint}")


def api_post(path: str, email: str, token: str, body: dict) -> dict:
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        f"{JIRA_BASE_URL}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        hint = " (JIRA_API_TOKENが無効・期限切れの可能性があります)" if e.code == 401 else ""
        raise JiraApiError(f"POST {JIRA_BASE_URL}{path} failed: HTTP {e.code} {e.reason}: {body_text}{hint}")


def fetch_summaries(issue_keys: list[str], email: str, token: str) -> dict[str, str]:
    """指定したticket keyの一覧について、summary(件名)をまとめて取得する。"""
    unique_keys = sorted(set(issue_keys))
    if not unique_keys:
        return {}
    jql = f"key in ({','.join(unique_keys)})"
    body = {"jql": jql, "fields": ["summary"], "maxResults": 50}
    summaries: dict[str, str] = {}
    while True:
        data = api_post("/rest/api/3/search/jql", email, token, body)
        for issue in data.get("issues", []):
            summaries[issue["key"]] = issue.get("fields", {}).get("summary", "")
        if data.get("isLast", True) or not data.get("nextPageToken"):
            break
        body["nextPageToken"] = data["nextPageToken"]
    return summaries


def find_issue_keys(from_date: date, to_date: date, email: str, token: str) -> list[str]:
    """指定期間に自分(worklogAuthor)のworklogが1件でもあるissueのkeyを検索する。"""
    jql = (
        f'worklogAuthor = currentUser() AND worklogDate >= "{from_date.isoformat()}" '
        f'AND worklogDate <= "{to_date.isoformat()}"'
    )
    body = {"jql": jql, "fields": ["key"], "maxResults": 50}
    keys = []
    while True:
        data = api_post("/rest/api/3/search/jql", email, token, body)
        keys.extend(issue["key"] for issue in data.get("issues", []))
        if data.get("isLast", True) or not data.get("nextPageToken"):
            break
        body["nextPageToken"] = data["nextPageToken"]
    return keys


def adf_text(node) -> str:
    """ADF(dict)から素朴にテキストを取り出す。commentがADFで返ってきた場合のフォールバック用。"""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    texts = [node.get("text", "")]
    for c in node.get("content", []):
        texts.append(adf_text(c))
    return " ".join(t for t in texts if t).strip()


def parse_started(text: str) -> datetime:
    # worklog_jira_api.resolve_started()が生成する形式と同じ: 2021-01-17T12:34:00.000+0900
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%f%z")


def fetch_worklogs(issue_key: str, from_date: date, to_date: date, email: str, token: str) -> list[dict]:
    """指定issueの、指定期間・自分(email)のworklogだけを抽出して返す。"""
    data = api_get(f"/rest/api/2/issue/{issue_key}/worklog", email, token)
    result = []
    for w in data.get("worklogs", []):
        started = parse_started(w["started"]).astimezone()
        if not (from_date <= started.date() <= to_date):
            continue
        author_email = (w.get("author") or {}).get("emailAddress")
        if author_email and author_email.lower() != email.lower():
            continue
        result.append(
            {
                "id": w["id"],
                "issue": issue_key,
                "date": started.date(),
                "started": started,
                "seconds": w["timeSpentSeconds"],
                "comment": adf_text(w.get("comment", "")),
                "created": w.get("created", ""),
            }
        )
    return result


def fetch_all_worklogs(from_date: date, to_date: date, email: str, token: str) -> list[dict]:
    """期間内に自分のworklogがあるissueを検索し、各issueの期間内worklogをまとめて返す。"""
    entries = []
    for issue_key in find_issue_keys(from_date, to_date, email, token):
        entries.extend(fetch_worklogs(issue_key, from_date, to_date, email, token))
    return entries
