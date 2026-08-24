import http.server
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/calendar.events"
PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        self.server.auth_code = params.get("code", [None])[0]
        self.server.auth_error = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<html><body>認可が完了しました。このタブは閉じて構いません。</body></html>".encode())

    def log_message(self, format, *args):
        pass


def update_env_file(path: Path, updates: dict) -> None:
    lines = path.read_text().splitlines(keepends=True)
    seen = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                seen.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}\n")
    path.write_text("".join(new_lines))


def main() -> int:
    env_path = Path(os.environ.get("GCAL_ENV_FILE", Path(__file__).parent / ".env"))
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        fail("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET is not set (check .env). See step 1 in get_credentials.sh's comments.")

    server = http.server.HTTPServer(("127.0.0.1", 0), CallbackHandler)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}"

    auth_params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    print("以下のURLをブラウザ(WSLと同じマシン上のブラウザ)で開き、ログイン→「許可」をクリックしてください。", file=sys.stderr)
    print(f"  {AUTH_URL}?{auth_params}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"(認可完了を待っています。127.0.0.1:{port} で応答を待機中...)", file=sys.stderr)

    server.timeout = 300
    server.handle_request()

    auth_code = getattr(server, "auth_code", None)
    auth_error = getattr(server, "auth_error", None)
    if auth_error:
        fail(f"authorization failed: {auth_error}")
    if not auth_code:
        fail("timed out waiting for the browser redirect (5分経過)。再実行してください。")

    data = urllib.parse.urlencode(
        {
            "code": auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req) as res:
            body = json.load(res)
    except urllib.error.HTTPError as e:
        fail(f"token exchange failed: HTTP {e.code} {e.reason}: {e.read().decode(errors='replace')}")

    if "refresh_token" not in body:
        fail(
            "レスポンスにrefresh_tokenが含まれていません(既に一度許可済みだと再度発行されないことがあります)。"
            "Googleアカウントの「サードパーティ製アプリとサービス」からこのアプリのアクセスを取り消してから再実行してください。"
        )

    updates = {"GOOGLE_ACCESS_TOKEN": body["access_token"], "GOOGLE_REFRESH_TOKEN": body["refresh_token"]}
    update_env_file(env_path, updates)
    print(f"{PROG}: updated {env_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
