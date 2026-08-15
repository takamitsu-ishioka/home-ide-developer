# .home-ide-developer

「ルート・ローカル・リポジトリ」（`~/`にcloneされたhome-ide-developer。
他のローカルリポジトリを物理的に内包する、この Linux ユーザーにとっての
ルート）専用のデータ置き場です。ディレクトリの**名前そのもの**が、この
リポジトリの正式名称のローカルキャッシュでもあります。

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

## 名前の更新の仕組み

`~/bin/repo_name_sync.sh` が Claude Code の SessionStart フックから
自動実行され、`git remote get-url origin` から取得した現在の名前と、
このディレクトリの名前を突き合わせて必要ならリネームします
（`.claude/settings.json` の `hooks.SessionStart` を参照）。`mv`による
ディレクトリごとのリネームなので、中身のファイルは自動的について
きます。

どのディレクトリが「マーカー」かは、中の `.repo-name-marker`
（空ファイル）の存在で識別しています。名前は変わり得るので、名前では
なく印(このファイル)で追跡します。他のスクリプトがこのディレクトリの
パスを知りたいときは、パスをハードコードせず `repo_local_dir.sh` で
毎回解決してください。

## 中身

- `README.md` — 本ファイル（追跡対象）
- `.repo-name-marker` — マーカー識別用の空ファイル（追跡対象）
- `environment_name` / `environment_name.template` — このマシンの環境名
  (LOCAL/ALPHA/BETA/PROD)。`.env`と同様、実体(`environment_name`)は
  machine-local につき.gitignore対象、テンプレートのみ追跡
- `current_repo` — Claude Codeセッションの「カレント・リポジトリ」状態
  (`current_repo_set.sh`が自動生成。machine-localにつき.gitignore対象)

「ルート・ローカル・リポジトリ」であるがゆえに、複数のローカルリポジトリ
(例: `ghost`)を横断する状態も、ここにまとめて置いています。
