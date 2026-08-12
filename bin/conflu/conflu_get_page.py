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
    print(f"usage: {name} <page_id>", file=sys.stderr)
    print(f"example: {name} 942571521", file=sys.stderr)
    sys.exit(1)


def api_get(base_url, email, token, path):
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        f"{base_url}/{path}",
        headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        usage()
    page_id = sys.argv[1]

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
    page = api_get(
        base_url, env["CONFLU_EMAIL"], env["CONFLU_TOKEN"],
        f"rest/api/content/{page_id}?expand=body.storage,version,ancestors",
    )

    out = {
        "id": page["id"],
        "title": page["title"],
        "version": page["version"]["number"],
        "space_key": page.get("space", {}).get("key"),
        "parent_id": page["ancestors"][-1]["id"] if page.get("ancestors") else None,
        "url": base_url + page["_links"]["webui"],
        "body_storage": page["body"]["storage"]["value"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
