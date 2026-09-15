#!/usr/bin/env python3
import sys
import re
import os
import glob


def usage():
    name = os.path.basename(sys.argv[0])
    script_dir = os.path.dirname(os.path.realpath(__file__))
    regex_dir = os.path.join(script_dir, "replace.regex")
    names = sorted(
        os.path.splitext(os.path.basename(f))[0]
        for f in glob.glob(os.path.join(regex_dir, "*.regex"))
    )
    print(f"{name}: Too few arguments", file=sys.stderr)
    print(f"usage: {name} <names> [file]", file=sys.stderr)
    print(f"example: {name} bold,chatgpt,me note.md", file=sys.stderr)
    print(f"example: cat note.md | {name} bold,me > out.md", file=sys.stderr)
    print(f"regex dir: {regex_dir}/", file=sys.stderr)
    print(f"available: {','.join(names)}", file=sys.stderr)
    sys.exit(1)


def load_regex(regex_name):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    regex_file = os.path.join(script_dir, "replace.regex", f"{regex_name}.regex")
    with open(regex_file, encoding="utf-8") as f:
        lines = f.read().splitlines()
    pattern = lines[0]
    replacement = re.sub(r'\$(\d+)', r'\\\1', lines[1])
    return pattern, replacement


def apply_spsp(content, pattern, replacement):
    """Apply spsp outside fenced code and display-math blocks."""
    result = []
    in_fence = False
    fence_char = None
    in_math = False

    for line in content.splitlines(keepends=True):
        body = line[:-1] if line.endswith("\n") else line
        newline = "\n" if line.endswith("\n") else ""
        unquoted = re.sub(r"^(?:> *)*", "", body)

        fence = re.match(r"^(`{3,}|~{3,})", unquoted)
        if fence:
            char = fence.group(1)[0]
            if not in_math and (not in_fence or char == fence_char):
                in_fence = not in_fence
                fence_char = char if in_fence else None
            result.append(line)
            continue

        math_delimiter = unquoted.strip()
        if not in_fence and math_delimiter in {"$$", r"\[", r"\]"}:
            if math_delimiter == "$$":
                in_math = not in_math
            elif math_delimiter == r"\[":
                in_math = True
            else:
                in_math = False
            result.append(line)
            continue

        if in_fence or in_math:
            result.append(line)
            continue

        result.append(re.sub(pattern, replacement, body) + newline)

    return "".join(result)


def apply_codebold(content):
    """Remove Markdown bold markers only inside fenced code blocks."""
    result = []
    in_fence = False
    fence_char = None
    bold = re.compile(r"\*\*(?=\S)(.*?\S)\*\*")

    for line in content.splitlines(keepends=True):
        unquoted = re.sub(r"^(?:> *)*", "", line)
        fence = re.match(r"^(`{3,}|~{3,})", unquoted)
        if fence:
            char = fence.group(1)[0]
            if not in_fence or char == fence_char:
                in_fence = not in_fence
                fence_char = char if in_fence else None
            result.append(line)
            continue

        if in_fence:
            prev = None
            while prev != line:
                prev = line
                line = bold.sub(r"\1", line)
        result.append(line)

    return "".join(result)


def apply_all(content, regex_names):
    for name in regex_names:
        if name == "codebold":
            content = apply_codebold(content)
            continue
        pattern, replacement = load_regex(name)
        if name == "spsp":
            content = apply_spsp(content, pattern, replacement)
            continue
        prev = None
        while prev != content:
            prev = content
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    return content


def main():
    if len(sys.argv) < 2:
        usage()

    names = [n.strip() for n in sys.argv[1].split(",") if n.strip()]

    if len(sys.argv) >= 3:
        filepath = sys.argv[2]
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        result = apply_all(content, names)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result)
    else:
        content = sys.stdin.read()
        result = apply_all(content, names)
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
