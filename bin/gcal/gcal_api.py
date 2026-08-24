import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

import refresh_access_token

API_BASE_URL = "https://www.googleapis.com/calendar/v3"


class GcalApiError(Exception):
    pass


def resolve_date(text: str) -> date:
    """'TODAY'/'TOMORROW'/'YYYY-MM-DD'をdateへ解決する。不正な形式はValueErrorを送出する(呼び出し側でfail())。"""
    if text == "TODAY":
        return date.today()
    if text == "TOMORROW":
        return date.today() + timedelta(days=1)
    return date.fromisoformat(text)


def events_path(calendar_id: str) -> str:
    return f"/calendars/{urllib.parse.quote(calendar_id, safe='')}/events"


def event_path(calendar_id: str, event_id: str) -> str:
    return f"{events_path(calendar_id)}/{urllib.parse.quote(event_id, safe='')}"


def refresh_expired_token() -> str:
    env_path = refresh_access_token.default_env_path()
    try:
        updates = refresh_access_token.refresh(env_path)
    except Exception as e:
        raise GcalApiError(f"access_tokenが期限切れですが、自動更新に失敗しました: {e}")
    print(f"gcal_api: access_tokenが期限切れだったため自動更新しました({env_path})", file=sys.stderr)
    return updates["GOOGLE_ACCESS_TOKEN"]


def api_post(path: str, access_token: str, body: dict, allow_refresh: bool = True) -> tuple[dict, str]:
    req = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res), access_token
    except urllib.error.HTTPError as e:
        if e.code == 401 and allow_refresh:
            return api_post(path, refresh_expired_token(), body, allow_refresh=False)
        error_body = e.read().decode(errors="replace")
        raise GcalApiError(f"POST {path} failed: HTTP {e.code} {e.reason}: {error_body}")


def api_get(path: str, access_token: str, allow_refresh: bool = True) -> tuple[dict, str]:
    req = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res), access_token
    except urllib.error.HTTPError as e:
        if e.code == 401 and allow_refresh:
            return api_get(path, refresh_expired_token(), allow_refresh=False)
        error_body = e.read().decode(errors="replace")
        raise GcalApiError(f"GET {path} failed: HTTP {e.code} {e.reason}: {error_body}")


def api_patch(path: str, access_token: str, body: dict, allow_refresh: bool = True) -> tuple[dict, str]:
    req = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res), access_token
    except urllib.error.HTTPError as e:
        if e.code == 401 and allow_refresh:
            return api_patch(path, refresh_expired_token(), body, allow_refresh=False)
        error_body = e.read().decode(errors="replace")
        raise GcalApiError(f"PATCH {path} failed: HTTP {e.code} {e.reason}: {error_body}")


def parse_reminder_minutes(text: str) -> int:
    """通知時刻(HH:MM、"予定の何時間何分前か")を分に変換する。'none'は呼び出し側で別扱いする。"""
    hours, _, minutes = text.partition(":")
    return int(hours) * 60 + int(minutes)


def format_reminder_minutes(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def format_overrides(overrides: list) -> str:
    if not overrides:
        return "none"
    parts = [f"{o.get('method')}:{format_reminder_minutes(o['minutes'])}" for o in overrides]
    return ",".join(parts)


def api_delete(path: str, access_token: str, allow_refresh: bool = True) -> str:
    req = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            res.read()
            return access_token
    except urllib.error.HTTPError as e:
        if e.code == 401 and allow_refresh:
            return api_delete(path, refresh_expired_token(), allow_refresh=False)
        if e.code == 410:
            raise GcalApiError(f"DELETE {path} failed: HTTP 410 Gone(既に削除済みの可能性があります)")
        error_body = e.read().decode(errors="replace")
        raise GcalApiError(f"DELETE {path} failed: HTTP {e.code} {e.reason}: {error_body}")
