#!/usr/bin/env python

import json
import subprocess
import sys


def build_graphql_query(owner, repo, pr_number):
    return f"""
{{
  repository(owner: "{owner}", name: "{repo}") {{
    pullRequest(number: {pr_number}) {{
      title
      url
      body

      reviewThreads(first: 100) {{
        nodes {{
          isResolved

          comments(first: 100) {{
            nodes {{
              author {{
                login
              }}

              body
              path
              line
              createdAt
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""


def decode_output(data: bytes) -> str:
    decode_candidates = [
        "utf-8",
        "cp932",
        "shift_jis",
    ]

    for enc in decode_candidates:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass

    raise RuntimeError("Failed to decode gh output")


def main(owner, repo, pr_number):
    #
    # Windows console を UTF-8 に
    #
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    graphql_query = build_graphql_query(owner, repo, pr_number)

    cmd = [
        "gh",
        "api",
        "graphql",
        "-f",
        f"query={graphql_query}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("gh api graphql failed", file=sys.stderr)

        try:
            stderr_text = decode_output(e.stderr)
            print(stderr_text, file=sys.stderr)
        except Exception:
            print(repr(e.stderr), file=sys.stderr)

        sys.exit(e.returncode)

    try:
        text = decode_output(result.stdout)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print("Failed to parse JSON output", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <owner> <repo> <pr_number>",
            file=sys.stderr,
        )
        sys.exit(1)

    main(
        sys.argv[1],
        sys.argv[2],
        int(sys.argv[3]),
    )
