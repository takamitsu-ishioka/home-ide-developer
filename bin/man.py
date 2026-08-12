#!/usr/bin/env python3
"""
List commands in ~/bin with descriptions, or navigate subdirectories.
Tree-format display with configurable depth and width.

Usage:
  man.sh [OPTIONS] [PATH|COMMAND]

OPTIONS:
  --depth N       Maximum tree depth to display (default: 2, env: MAN_DEPTH)
  --width N       Maximum items per directory (default: unlimited, env: MAN_WIDTH)
  --help          Show this help message

EXAMPLES:
  man.sh                           # Show ~/bin tree (depth 2)
  man.sh mmwave                    # Show mmwave subtree
  man.sh mmwave/blob               # Show blob subtree
  man.sh --depth 3 mmwave          # Show mmwave with depth 3
  man.sh --width 10 mmwave         # Show mmwave with max 10 items per dir
  man.sh azure_storage_explore.sh  # Show file details
"""

import os
import sys
import argparse
from pathlib import Path


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


def tree_walk(directory, prefix="", depth=0, max_depth=2, max_width=0):
    """Walk directory tree and print with tree format."""

    # Collect files and dirs, preserving `ls`-style alphabetical order
    # (do not bucket by type, or the tree order won't match `ls`)
    all_items = []

    try:
        for item in sorted(os.listdir(directory)):
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
            print(f"{prefix}{branch}{item_name}")
        elif item_type == 'dir':
            # Check if directory is empty
            try:
                contents = [x for x in os.listdir(item_path) if not is_ignored(os.path.join(item_path, x), item_path)]
                is_empty = len(contents) == 0
            except PermissionError:
                is_empty = False

            if is_empty:
                print(f"{prefix}{branch}{item_name}/ (empty)")
            else:
                print(f"{prefix}{branch}{item_name}/")
                if depth < max_depth:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    tree_walk(item_path, next_prefix, depth + 1, max_depth, max_width)
        elif item_type == 'ignored':
            print(f"{prefix}{branch}{item_name}/ (ignored)")

    # Print "(N more)" if items were truncated
    if more_count > 0:
        is_last = True
        branch = "└── "
        print(f"{prefix}{branch}({more_count} more)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--depth', type=int, default=None, help='Maximum tree depth (default: 2)')
    parser.add_argument('--width', type=int, default=None, help='Maximum items per directory (default: unlimited)')
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
        else:
            target_dir = None
            display_name = args.target

    if target_dir is None:
        print(f"man.sh: not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    if os.path.isdir(target_dir):
        print(display_name)
        tree_walk(target_dir, "", 0, max_depth, max_width)
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
