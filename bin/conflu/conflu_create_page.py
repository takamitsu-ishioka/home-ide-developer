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
    print(f"{name}: input is required", file=sys.stderr)
    print(f"usage: {name} [--dry-run]", file=sys.stderr)
    print(f"example: {name} < page.jsonc", file=sys.stderr)
    sys.exit(1)


def create_page(env: dict, page: dict) -> dict:
    base_url = env["CONFLU_BASE_URL"].rstrip("/")
    credentials = base64.b64encode(
        f"{env['CONFLU_EMAIL']}:{env['CONFLU_TOKEN']}".encode()
    ).decode()

    payload = {
        "type": "page",
        "title": page["title"],
        "space": {"key": page.get("space_key", env.get("CONFLU_SPACE_KEY"))},
        "body": {"storage": {"value": page["body_storage"], "representation": "storage"}},
    }
    if page.get("parent_id"):
        payload["ancestors"] = [{"id": page["parent_id"]}]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/rest/api/content",
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    if sys.stdin.isatty():
        usage()

    dry_run = "--dry-run" in sys.argv[1:]

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

    try:
        lines = [l for l in sys.stdin if not l.lstrip().startswith("//")]
        page = json.loads("".join(lines))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    for key in ("title", "body_storage"):
        if key not in page:
            print(f"Error: '{key}' is required in JSON input", file=sys.stderr)
            sys.exit(1)
    if not page.get("space_key") and not env.get("CONFLU_SPACE_KEY"):
        print("Error: 'space_key' is required (JSON input or CONFLU_SPACE_KEY in .env)", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(json.dumps(page, ensure_ascii=False, indent=2))
        return

    try:
        result = create_page(env, page)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    base_url = env["CONFLU_BASE_URL"].rstrip("/")
    print(f"{result['id']}: {base_url}{result['_links']['webui']}")


if __name__ == "__main__":
    main()
