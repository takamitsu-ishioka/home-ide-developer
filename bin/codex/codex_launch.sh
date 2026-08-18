#!/bin/bash
# codex をセッション選択つきで起動する
# 引数なし: どちらにするかを対話的に尋ねる
# resume : 既存セッションをピッカー(codex resume)で選ばせて再開
# new    : 新しいセッションを開始する(任意で最初のプロンプトを渡せる)
# 注: codex には claude の -n(セッション名を指定して開始)に相当するCLIオプションが無い。
#     そのため new モードでは「名前」ではなく「最初のプロンプト」を任意で受け取る。

SCRIPT=$(basename "$0")

function echo2() {
  echo "$1" >&2
}

function usage() {
  echo2 "$SCRIPT: $1"
  echo2 "usage: $SCRIPT [resume|new] [initial_prompt]"
  echo2 "example: $SCRIPT"
  echo2 "example: $SCRIPT resume"
  echo2 "example: $SCRIPT new \"note記事の下書き整理\""
  exit 1
}

function launch_resume() {
  exec codex resume
}

function launch_new() {
  local prompt="$1"
  if [ -n "$prompt" ]; then
    exec codex "$prompt"
  else
    exec codex
  fi
}

case "$#" in
  0)
    echo2 "1) 既存セッションから選ぶ (resume)"
    echo2 "2) 新しいセッションを開始する (new)"
    read -r -p "選択 [1/2]: " choice
    case "$choice" in
      1) launch_resume ;;
      2)
        read -r -p "最初のプロンプト(省略可): " prompt
        launch_new "$prompt"
        ;;
      *) usage "不正な選択です: $choice" ;;
    esac
    ;;
  1)
    case "$1" in
      resume) launch_resume ;;
      new) launch_new "" ;;
      *) usage "不明なモードです: $1" ;;
    esac
    ;;
  2)
    case "$1" in
      new) launch_new "$2" ;;
      *) usage "不明なモードです: $1" ;;
    esac
    ;;
  *)
    usage "引数の数が不正です"
    ;;
esac
