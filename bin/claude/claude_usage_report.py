"""Extract token usage from one Claude Code JSON result.

This is the implementation for claude_usage_report.sh and is not intended to
be run directly.
"""

import json
import sys
from typing import Any


TOKEN_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


def fail(message: str) -> None:
    print(f"claude_usage_report.py: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_result() -> dict[str, Any]:
    try:
        result = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        fail(f"Claude output is not valid JSON: {error}")

    if not isinstance(result, dict):
        fail("Claude JSON result is not an object")

    usage = result.get("usage")
    if not isinstance(usage, dict):
        fail("Claude JSON result has no usage object")

    return usage


def token_value(usage: dict[str, Any], field: str) -> int:
    value = usage.get(field, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        fail(f"usage.{field} is not an integer")
    if value < 0:
        fail(f"usage.{field} is negative")
    return value


def collect(usage: dict[str, Any]) -> dict[str, int]:
    if not any(field in usage for field in TOKEN_FIELDS):
        fail("Claude usage object has no recognized token fields")

    report = {field: token_value(usage, field) for field in TOKEN_FIELDS}
    report["total_tokens"] = sum(report.values())
    return report


def write_report(report: dict[str, int], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("\t".join(report))
    print("\t".join(str(value) for value in report.values()))


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"json", "tsv"}:
        fail("expected one output-format argument: json or tsv")

    write_report(collect(parse_result()), sys.argv[1])


if __name__ == "__main__":
    main()
