# .home-ide-developer

このディレクトリの**名前そのもの**が、このリポジトリの正式名称のローカルキャッシュです。

## 背景

このリポジトリはホームディレクトリ直下（`~/`）にcloneされているため、`~/`
のbasename（Linuxユーザー名 `developer`）とGitHub上のリポジトリ名
（`home-ide-developer`）が一致しません。

「ディレクトリ名から拾えるから」という理由でユーザー名や`git remote`の
URLをその場で解析して名前として使うと、たまたま合っている場合にしか
動かないバグの温床になります（実例: `whereami.sh`が最初のバージョンで
`git rev-parse --show-toplevel`のbasenameを使い、`developer`と誤表示
していました）。

一次情報（SSoT）はあくまでGitHub側のリポジトリ名です。このディレクトリは
それをディレクトリ名という形でローカルにキャッシュしたものにすぎません
（`~/.claude/CLAUDE.md`大前提1: 実装=ディレクトリ名構造がSSoTを直接表現する、
という考え方の応用）。キャッシュである以上、GitHub側で名前が変わったら
追従して更新する必要があります。

## 更新の仕組み

`~/bin/repo_name_sync.sh` が Claude Code の SessionStart フックから
自動実行され、`git remote get-url origin` から取得した現在の名前と、
このディレクトリの名前を突き合わせて必要ならリネームします
（`.claude/settings.json` の `hooks.SessionStart` を参照）。

どのディレクトリが「マーカー」かは、中の `.repo-name-marker`
（空ファイル）の存在で識別しています。名前は変わり得るので、名前では
なく印(このファイル)で追跡します。

## 使い方

ツールから参照する場合は、`~/.<何か>`ではなく、このディレクトリの
**存在と名前**を見てください。中身のファイルは`README.md`と
`.repo-name-marker`のみ（このリポジトリ専用の他のデータを置く場所と
しても使えます）。
