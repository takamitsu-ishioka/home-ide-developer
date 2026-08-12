#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_URL = "https://accounts.secure.freee.co.jp/public_api/token"
REQUIRED_KEYS = ["FREEE_CLIENT_ID", "FREEE_CLIENT_SECRET", "FREEE_REFRESH_TOKEN"]


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


def main():
    env_path = Path(os.environ.get("FREEE_ENV_FILE", Path(__file__).parent / ".env"))
    if not env_path.exists():
        print(
            f"refresh_access_token.py: {env_path} not found. Copy {env_path.parent / '.env.template'} to {env_path} and fill it in.",
            file=sys.stderr,
        )
        sys.exit(1)

    env = load_env(env_path)
    for key in REQUIRED_KEYS:
        if not env.get(key):
            print(f"refresh_access_token.py: {key} is missing in {env_path}", file=sys.stderr)
            sys.exit(1)

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": env["FREEE_CLIENT_ID"],
            "client_secret": env["FREEE_CLIENT_SECRET"],
            "refresh_token": env["FREEE_REFRESH_TOKEN"],
        }
    ).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as res:
            body = json.load(res)
    except urllib.error.HTTPError as e:
        print(f"refresh_access_token.py: {e.code} {e.reason}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    # freee invalidates the refresh_token after a single use, so the new one
    # must be persisted or the next refresh will fail.
    update_env_file(
        env_path,
        {
            "FREEE_ACCESS_TOKEN": body["access_token"],
            "FREEE_REFRESH_TOKEN": body["refresh_token"],
        },
    )
    print(f"refresh_access_token.py: updated {env_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
