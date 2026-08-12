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
    print(f"usage: {name} <space_key>", file=sys.stderr)
    print(f"example: {name} MMWAVE", file=sys.stderr)
    sys.exit(1)


def api_get(base_url: str, email: str, token: str, path: str) -> dict:
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(
        f"{base_url}/{path}",
        headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"conflu_tree.py: HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def print_tree(base_url: str, email: str, token: str, page: dict, depth: int):
    print("  " * depth + f"- {page['title']} (id={page['id']})")
    children = api_get(
        base_url, email, token, f"rest/api/content/{page['id']}/child/page?limit=100"
    )
    for child in children.get("results", []):
        print_tree(base_url, email, token, child, depth + 1)


def main():
    if len(sys.argv) != 2:
        usage()
    space_key = sys.argv[1]

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
    space = api_get(base_url, env["CONFLU_EMAIL"], env["CONFLU_TOKEN"], f"rest/api/space/{space_key}?expand=homepage")
    homepage = space.get("homepage")
    if not homepage:
        print(f"conflu_tree.py: space '{space_key}' has no homepage", file=sys.stderr)
        sys.exit(1)

    print_tree(base_url, env["CONFLU_EMAIL"], env["CONFLU_TOKEN"], homepage, 0)


if __name__ == "__main__":
    main()
