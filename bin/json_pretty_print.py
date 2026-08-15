#!/usr/bin/env python3
import sys
import os
import json


def usage(reason="Invalid arguments"):
    name = "json_pretty_print.py"
    print(f"{name}: {reason}", file=sys.stderr)
    print(f"usage: {name} [file]", file=sys.stderr)
    print(f"example: {name} data.json", file=sys.stderr)
    print(f"example: cat data.json | {name}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) > 2:
        usage()

    if len(sys.argv) == 2:
        path = sys.argv[1]
        if path.startswith("-"):
            usage(f"unknown option: {path}")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            usage(f"cannot open {path}: {e.strerror}")
    else:
        text = sys.stdin.read()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"json_pretty_print.py: JSON decode error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
