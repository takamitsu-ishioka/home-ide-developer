#!/bin/bash
# Windows側のネイティブVS Code実行ファイルを探して実行する
# （open_worktree.shのfind_code()と同じロジック）

find_code() {
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

CODE_BIN=$(find_code)

if [ -z "$CODE_BIN" ]; then
    echo "エラー: VS Codeの実行ファイルが見つかりません。" >&2
    exit 1
fi

exec "$CODE_BIN" "$@"
