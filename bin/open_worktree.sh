#!/bin/bash
# Open an existing worktree in VS Code (Remote-WSL) with one command.

SCRIPT=$(basename "$0")
DEFAULT_WORKTREES_ROOT="/mnt/c/Projects/mmwave/worktrees"
WORKTREES_ROOT="$DEFAULT_WORKTREES_ROOT"

function echo2() {
  echo -e "\033[1;34m$1\033[0m" >&2
}

function find_code() {
  # PATH経由のWindows interopは古いWSLセッションだとPATHが更新されず
  # 見つからないことがあるので、既知のインストール場所もフォールバックで探す
  if command -v code >/dev/null 2>&1; then
    command -v code
    return
  fi
  local candidates=(
    "/mnt/c/Program Files/Microsoft VS Code/bin/code"
    /mnt/c/Users/*/AppData/Local/Programs/"Microsoft VS Code"/bin/code
  )
  local f
  for f in "${candidates[@]}"; do
    if [ -x "$f" ]; then
      echo "$f"
      return
    fi
  done
}

function list_worktrees() {
  echo2 "Available worktrees under $WORKTREES_ROOT:"
  find "$WORKTREES_ROOT" -mindepth 1 -maxdepth 1 -type d -printf '  %f\n' | sort >&2
}

function usage() {
  echo2 "$SCRIPT: $*"
  echo2 "Usage: $SCRIPT [-r <worktrees-root>] <worktree-name-or-path>"
  echo2 "  -r <worktrees-root>  worktreeの親ディレクトリ。絶対/相対パス可。既定値: $DEFAULT_WORKTREES_ROOT"
  echo2 "  <worktree-name-or-path> が実在するディレクトリならそのまま開く。それ以外は <worktrees-root>/<name> として解決"
  echo2 "Example: $SCRIPT feature-448-use-diaper-change-for-sleep-onset-detection"
  echo2 "Example: $SCRIPT ./worktrees/455-remove-sleep-probability-customer-filter"
  echo2 "Example: $SCRIPT -r ../other-repo/worktrees some-branch"
  echo2 ""
  list_worktrees
  exit 1
}

while getopts "r:" opt; do
  case "$opt" in
    r) WORKTREES_ROOT="$OPTARG" ;;
    *) usage "Unknown option" ;;
  esac
done
shift $((OPTIND - 1))

if [ ! -d "$WORKTREES_ROOT" ]; then
  usage "worktrees root not found: $WORKTREES_ROOT"
fi
WORKTREES_ROOT="$(cd "$WORKTREES_ROOT" && pwd)"

if [ "$#" -ne 1 ]; then
  usage "Invalid number of arguments"
fi

NAME="$1"

if [ -d "$NAME" ]; then
  TARGET="$(cd "$NAME" && pwd)"
else
  TARGET="$WORKTREES_ROOT/$NAME"
  if [ ! -d "$TARGET" ]; then
    usage "Worktree not found: $NAME"
  fi
fi

CODE_BIN="$(find_code)"
if [ -z "$CODE_BIN" ]; then
  echo2 "$SCRIPT: 'code' コマンドが見つかりません。VS CodeのPATHが通っているか確認してください（\`wsl --shutdown\`で再起動すると直ることがあります）。"
  exit 1
fi

echo2 "Opening $TARGET in VS Code (Remote-WSL)..."
cd "$TARGET" && exec "$CODE_BIN" .
