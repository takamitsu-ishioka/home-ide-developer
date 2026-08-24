import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_URL = "https://oauth2.googleapis.com/token"
REQUIRED_KEYS = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]


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


def default_env_path() -> Path:
    return Path(os.environ.get("GCAL_ENV_FILE", Path(__file__).parent / ".env"))


def refresh(env_path: Path) -> dict:
    """Exchange the stored refresh_token for a new access_token, persist it to env_path, and return the updates.

    Googleのrefresh_tokenはfreeeと違い1回使っても無効化されない(ローテーションしない)ため、
    レスポンスにrefresh_tokenが含まれない限りGOOGLE_REFRESH_TOKENは書き換えない。
    """
    env = load_env(env_path)
    for key in REQUIRED_KEYS:
        if not env.get(key):
            raise KeyError(key)

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": env["GOOGLE_CLIENT_ID"],
            "client_secret": env["GOOGLE_CLIENT_SECRET"],
            "refresh_token": env["GOOGLE_REFRESH_TOKEN"],
        }
    ).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as res:
        body = json.load(res)

    updates = {"GOOGLE_ACCESS_TOKEN": body["access_token"]}
    if "refresh_token" in body:
        updates["GOOGLE_REFRESH_TOKEN"] = body["refresh_token"]
    update_env_file(env_path, updates)
    return updates


def main():
    env_path = default_env_path()
    if not env_path.exists():
        print(
            f"refresh_access_token.py: {env_path} not found. Copy {env_path.parent / '.env.template'} to {env_path} and fill it in.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        refresh(env_path)
    except KeyError as e:
        print(f"refresh_access_token.py: {e.args[0]} is missing in {env_path}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"refresh_access_token.py: {e.code} {e.reason}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    print(f"refresh_access_token.py: updated {env_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
