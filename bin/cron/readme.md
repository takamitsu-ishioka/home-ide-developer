# bin/cron/ — このマシンの定期実行(crond)の機構

「このマシン(LOCAL, WSL)の user crontab は、このリポジトリが所有する」。
`crontab -e` での手動編集はしない。ジョブの追加・変更は必ずこのディレクトリのファイルを
編集して commit し、`cron_register.sh` を再実行する。

ここに置くのは**機構だけ**。ジョブ本体は各ドメイン(`bin/due_watch/` 等)に置き、
crontab からは `cron_run.sh` 経由で名前で呼ぶ。

## ファイル

| ファイル | 役割 | git |
|---|---|---|
| `crontab` | user crontab 全体の権威マニフェスト。`cron_register.sh` が全置換で登録 | 追跡 |
| `cron_run.sh` | crontab の各行が呼ぶラッパー。`cron.env` を読んで env を揃えてから `exec "$@"` | 追跡 |
| `cron.env` | cron ジョブが必要とする最小の環境変数(PATH/TZ/LANG)。bash 構文 | 追跡 |
| `_cron.env` | マシン固有の env 上書き(任意)。あれば `cron_run.sh` が `cron.env` の後に読む | gitignore (`_*`) |
| `cron_register.sh` | `crontab` を登録 + crond 稼働確認 | 追跡 |

## 使い方

```bash
# 差分だけ見る(登録しない)
~/bin/cron/cron_register.sh --dry-run

# 登録(y/n 確認あり)
~/bin/cron/cron_register.sh --confirm

# 登録(確認なし)
~/bin/cron/cron_register.sh

# 登録内容の確認
crontab -l
```

WSL では crond が自動起動しない。`cron_register.sh` が稼働確認し、止まっていれば
`sudo service cron start` を促す(自動では起動しない)。

## ジョブの追加手順

1. ジョブ本体を該当ドメインに作る(例: `bin/due_watch/due_watch_poll.sh`)。
   **非対話であること** — cron 下では stdin が無く `--confirm` の y/n は機能しない。
   副作用ゲートのある処理(外部サービスへの書き込み等)はジョブに含めず、人間セッションで行う。
2. そのジョブが別ドメインのツールを名前で呼ぶなら、そのディレクトリを `cron.env` の
   `PATH` に足す(PATH は再帰しないため)。
3. `crontab` に1行足す。書式:
   ```
   <分> <時> <日> <月> <曜> "$HOME/bin/cron/cron_run.sh" <command> [args...] >> "$HOME/bin/<domain>/_<job>.log" 2>&1
   ```
   - env 代入行(`PATH=` 等)は `crontab` に置かない。crond はこの行を shell 展開しないので
     `$HOME` が使えず絶対パスになる。環境は `cron_run.sh` が `cron.env` から与える。
   - コマンド欄は crond が `$SHELL -c` に渡すので `$HOME` は展開される。
   - ログは `_` 接頭辞にして gitignore に乗せる。
4. `cron_register.sh --confirm` で反映。
5. `crontab` の変更を commit。

## 設計メモ

- crond は最小環境(PATH ほぼ無し、TZ・LANG 未定、`~/bin/*` に PATH 通らず)でジョブを起動する。
  対話シェルの PATH は `.bashrc`(マシン固有・gitignore)が組み立てているが、cron ジョブが
  これに依存すると再現不能になる。必要な env は `cron.env` に**明示宣言**する
  (「実装がモデルを直接表現する」)。
- 「登録時に `env` をスナップショットして crontab へ流し込む」方式は採らない
  (セッション固有の値やシークレットを固定し、すぐ陳腐化する)。実行時に `cron_run.sh` が
  最小 env へ揃える。
- 単発ジョブ(`at`/`atd`)が必要になったら別途検討。`atd` は投入時の環境をスナップショット
  するので事情が違う。今は作らない。
