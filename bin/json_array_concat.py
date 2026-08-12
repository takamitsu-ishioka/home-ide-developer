#!/usr/bin/env python3
import sys
import os
import json


def usage(reason="Invalid arguments"):
    name = "json_array_concat.py"
    print(f"{name}: {reason}", file=sys.stderr)
    print(f"usage: {name} <file1.json> [file2.json ...]", file=sys.stderr)
    print(f"example: {name} a.json b.json > merged.json", file=sys.stderr)
    print(f"example: {name} dir/*/*.json | sleep_probability_calculate.sh 0 json", file=sys.stderr)
    sys.exit(1)


def main():
    paths = sys.argv[1:]
    if not paths:
        usage("no input files given")

    merged = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            usage(f"cannot open {path}: {e.strerror}")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            usage(f"{path}: JSON decode error: {e}")

        if not isinstance(data, list):
            usage(f"{path}: top-level JSON must be an array (got {type(data).__name__})")

        merged.extend(data)

    print(json.dumps(merged, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
