#!/usr/bin/env python3
import base64
import json
import os
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


def usage():
    name = Path(__file__).name
    print(f"{name}: Too few arguments", file=sys.stderr)
    print(f"usage: {name} <page_id> <new_parent_id>", file=sys.stderr)
    print(f"example: {name} 942178361 1114413", file=sys.stderr)
    sys.exit(1)


def api_call(base_url, email, token, path, method="GET", payload=None):
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{base_url}/{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) != 3:
        usage()
    page_id, new_parent_id = sys.argv[1], sys.argv[2]

    env_path = Path(os.environ.get("CONFLU_ENV_FILE", Path(__file__).parent / ".env"))
    if not env_path.exists():
        print(
            f"Error: .env not found. Copy {env_path.parent / '.env.example'} to {env_path} and fill it in.",
            file=sys.stderr,
        )
        sys.exit(1)

    env = load_env(env_path)
    for key in ("CONFLU_EMAIL", "CONFLU_TOKEN", "CONFLU_BASE_URL"):
        if key not in env:
            print(f"Error: {key} is missing in {env_path}", file=sys.stderr)
            sys.exit(1)

    base_url = env["CONFLU_BASE_URL"].rstrip("/")
    current = api_call(
        base_url, env["CONFLU_EMAIL"], env["CONFLU_TOKEN"],
        f"rest/api/content/{page_id}?expand=version",
    )

    payload = {
        "id": page_id,
        "type": current["type"],
        "title": current["title"],
        "version": {"number": current["version"]["number"] + 1},
        "ancestors": [{"id": new_parent_id}],
    }

    result = api_call(
        base_url, env["CONFLU_EMAIL"], env["CONFLU_TOKEN"],
        f"rest/api/content/{page_id}", method="PUT", payload=payload,
    )
    print(f"{result['id']}: {base_url}{result['_links']['webui']}")


if __name__ == "__main__":
    main()
