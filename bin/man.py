#!/usr/bin/env python3
"""
List commands in ~/bin with descriptions, or navigate subdirectories.
Tree-format display with configurable depth and width.

Usage:
  man.sh [OPTIONS] [PATH|COMMAND]

OPTIONS:
  --depth N       Maximum tree depth to display (default: 2, env: MAN_DEPTH)
  --width N       Maximum items per directory (default: unlimited, env: MAN_WIDTH)
  -A, --all       Show dotfiles too (hidden by default, like ls -A)
  --help          Show this help message

EXAMPLES:
  man.sh                           # Show ~/bin tree (depth 2)
  man.sh mmwave                    # Show mmwave subtree
  man.sh mmwave/blob               # Show blob subtree
  man.sh --depth 3 mmwave          # Show mmwave with depth 3
  man.sh --width 10 mmwave         # Show mmwave with max 10 items per dir
  man.sh -A                        # Also show dotfiles
  man.sh azure_storage_explore.sh  # Show file details
"""

import os
import subprocess
import sys
import argparse
from pathlib import Path


def git_repo_name(path):
    """If `path` is a git repository root, return its name (from the
    "origin" remote's URL, falling back to the directory's own basename
    when there's no remote) -- else None. The remote's own name is
    preferred because a checkout directory's basename need not match it
    (e.g. this repo is cloned at ~/, whose basename is the Linux username
    "developer", not the GitHub repo name "home-ide-developer")."""
    if not os.path.exists(os.path.join(path, '.git')):
        return None
    try:
        result = subprocess.run(
            ['git', '-C', path, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=5,
        )
    except OSError:
        result = None
    if result and result.returncode == 0 and result.stdout.strip():
        name = result.stdout.strip().rsplit('/', 1)[-1]
        if name.endswith('.git'):
            name = name[:-4]
        return name
    return os.path.basename(path.rstrip('/'))

# tree-style coloring: directories blue, executables green, everything else
# (markdown, Makefiles) uncolored, annotations dim. Auto-detected -- on only
# when stdout is a terminal and NO_COLOR isn't set, same convention `ls`/
# `grep`/`tree` use, so piped/redirected output stays plain.
COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')
BLUE = "\033[1;34m" if COLOR else ""
GREEN = "\033[1;32m" if COLOR else ""
DIM = "\033[2m" if COLOR else ""
RESET = "\033[0m" if COLOR else ""


def get_header_summary(file_path):
    """Extract first non-shebang comment line."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if not first_line.startswith('#!'):
                f.seek(0)
            for line in f:
                if line.startswith('#'):
                    return line[1:].strip()
                break
    except:
        pass
    return "(no description)"


def get_header_full(file_path):
    """Extract all leading comment lines."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if not first_line.startswith('#!'):
                f.seek(0)
            lines = []
            for line in f:
                if line.startswith('#'):
                    lines.append(line[1:].strip())
                else:
                    break
        return '\n'.join(lines) or "(no description)"
    except:
        return "(no description)"


def is_ignored(path, parent_dir):
    """Check if path is in .man_ignore rules."""
    basename = os.path.basename(path.rstrip('/'))

    # Check local .man_ignore
    local_ignore = os.path.join(parent_dir, '.man_ignore')
    if os.path.isfile(local_ignore):
        with open(local_ignore, 'r') as f:
            patterns = f.read().strip().split('\n')
            if basename in patterns:
                return True

    # Check global .man_ignore
    global_ignore = os.path.join(os.path.dirname(__file__), '.man_ignore')
    if os.path.isfile(global_ignore):
        with open(global_ignore, 'r') as f:
            patterns = f.read().strip().split('\n')
            if basename in patterns:
                return True

    return False


def find_command(bin_dir, name):
    """Search the ~/bin tree for a file named exactly `name`, the way a
    command is found by basename regardless of which subdirectory (e.g.
    bin/github/) it lives in. Skips dotdirs and .man_ignore'd dirs, same
    as the tree display. Returns the list of matching paths (0, 1, or
    more -- more means the name is ambiguous)."""
    matches = []
    for root, dirnames, filenames in os.walk(bin_dir):
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith('.') and not is_ignored(os.path.join(root, d), root)
        ]
        if name in filenames:
            matches.append(os.path.join(root, name))
    return matches


def tree_walk(directory, prefix="", depth=0, max_depth=2, max_width=0, show_all=False):
    """Walk directory tree and print with tree format."""

    # Collect files and dirs, preserving `ls`-style alphabetical order
    # (do not bucket by type, or the tree order won't match `ls`)
    all_items = []

    try:
        for item in sorted(os.listdir(directory)):
            if item.startswith('.') and not show_all:
                continue
            item_path = os.path.join(directory, item)

            if os.path.isfile(item_path):
                # Executable files (skip .py), .md files, or Makefiles
                # (entry points that are conventionally never chmod +x'd)
                is_makefile = item in ('Makefile', 'makefile', 'GNUmakefile')
                if (os.access(item_path, os.X_OK) and not item.endswith('.py')) or item.endswith('.md') or is_makefile:
                    all_items.append((item_path, 'file'))
            elif os.path.isdir(item_path):
                if is_ignored(item_path, directory):
                    all_items.append((item_path, 'ignored'))
                else:
                    all_items.append((item_path, 'dir'))
    except PermissionError:
        return

    # Limit by width if needed
    if max_width > 0 and len(all_items) > max_width:
        shown_items = all_items[:max_width]
        more_count = len(all_items) - max_width
    else:
        shown_items = all_items
        more_count = 0

    # Print items
    for i, (item_path, item_type) in enumerate(shown_items):
        is_last = (i == len(shown_items) - 1) and (more_count == 0)
        branch = "└── " if is_last else "├── "
        item_name = os.path.basename(item_path)

        if item_type == 'file':
            is_exec = os.access(item_path, os.X_OK)
            color = GREEN if is_exec else ""
            print(f"{prefix}{branch}{color}{item_name}{RESET}")
        elif item_type == 'dir':
            # Check if directory is empty (from what this tree would show:
            # dotfiles don't count as content unless show_all is set)
            try:
                contents = [
                    x for x in os.listdir(item_path)
                    if not is_ignored(os.path.join(item_path, x), item_path)
                    and (show_all or not x.startswith('.'))
                ]
                is_empty = len(contents) == 0
            except PermissionError:
                is_empty = False

            repo = git_repo_name(item_path)
            repo_suffix = f" {DIM}({repo}){RESET}" if repo else ""

            if is_empty:
                print(f"{prefix}{branch}{BLUE}{item_name}/{RESET}{repo_suffix} {DIM}(empty){RESET}")
            else:
                print(f"{prefix}{branch}{BLUE}{item_name}/{RESET}{repo_suffix}")
                if depth < max_depth:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    tree_walk(item_path, next_prefix, depth + 1, max_depth, max_width, show_all)
        elif item_type == 'ignored':
            print(f"{prefix}{branch}{DIM}{item_name}/ (ignored){RESET}")

    # Print "(N more)" if items were truncated
    if more_count > 0:
        is_last = True
        branch = "└── "
        print(f"{prefix}{branch}{DIM}({more_count} more){RESET}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--depth', type=int, default=None, help='Maximum tree depth (default: 2)')
    parser.add_argument('--width', type=int, default=None, help='Maximum items per directory (default: unlimited)')
    parser.add_argument('-A', '--all', action='store_true', help='Show dotfiles too (like ls -A; hidden by default)')
    parser.add_argument('target', nargs='?', default='.', help='Path or command to show')

    args = parser.parse_args()

    # Override with environment variables if not set
    max_depth = args.depth if args.depth is not None else int(os.environ.get('MAN_DEPTH', '2'))
    max_width = args.width if args.width is not None else int(os.environ.get('MAN_WIDTH', '0'))

    bin_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()

    # Determine target directory
    if args.target.startswith('/'):
        # Absolute path
        target_dir = args.target
        display_name = args.target
    else:
        # Relative path: try from cwd first, then from bin_dir
        cwd_target = os.path.join(cwd, args.target)
        bin_target = os.path.join(bin_dir, args.target)

        if os.path.exists(cwd_target):
            target_dir = cwd_target
            display_name = args.target
        elif os.path.exists(bin_target):
            target_dir = bin_target
            display_name = args.target
        elif '/' not in args.target:
            # Not found as a direct child of cwd or ~/bin -- try resolving
            # it as a command name anywhere in the ~/bin tree (e.g.
            # bin/github/github_repos_list.sh, found by just the basename).
            matches = find_command(bin_dir, args.target)
            if len(matches) == 1:
                target_dir = matches[0]
                display_name = os.path.relpath(matches[0], bin_dir)
            elif len(matches) > 1:
                print(f"man.sh: ambiguous command: {args.target}", file=sys.stderr)
                for m in matches:
                    print(f"  {os.path.relpath(m, bin_dir)}", file=sys.stderr)
                sys.exit(1)
            else:
                target_dir = None
                display_name = args.target
        else:
            target_dir = None
            display_name = args.target

    if target_dir is None:
        print(f"man.sh: not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    if os.path.isdir(target_dir):
        repo = git_repo_name(target_dir)
        print(f"{display_name} {DIM}({repo}){RESET}" if repo else display_name)
        tree_walk(target_dir, "", 0, max_depth, max_width, args.all)
    elif os.path.isfile(target_dir):
        # Show file details
        print(display_name)
        print("----")
        print(get_header_full(target_dir))
    else:
        print(f"man.sh: not found: {args.target}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
