import os
import subprocess
import sys

PROG = os.path.basename(__file__)


def fail(message: str) -> None:
    print(f"{PROG}: {message}", file=sys.stderr)
    sys.exit(1)


def convert_file(path: str) -> None:
    result = subprocess.run(["jsonl_pretty_print.sh", path], capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"{path}: jsonl_pretty_print.shが失敗しました: {result.stderr.strip()}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(result.stdout)

    print(f"{PROG}: {path}をjsonl_pretty_print.shの出力で書き換えました", file=sys.stderr)


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        fail(f"usage: {PROG} <file>...")

    for path in paths:
        convert_file(path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
