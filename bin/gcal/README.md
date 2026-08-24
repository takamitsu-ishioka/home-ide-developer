# Google Calendar連携

Claude Codeが「あとで思い出してほしい予定」をGoogle Calendarへ登録するための最小限のツール。
bin/freee/と同型(OAuth2、`.env`にトークンを保持、401検知でreactiveにリフレッシュ)。

## 初回セットアップ

```bash
cp .env.template .env
./get_credentials.sh
```

手順の詳細(GCPでのOAuthクライアント作成、ループバックリダイレクトでの認可)は
`get_credentials.sh`冒頭のコメントを参照。OAuthクライアントの種類は必ず「デスクトップ アプリ」を選ぶこと
(「テレビと入力が限られたデバイス」はcalendar系スコープを扱えず`invalid_scope`になる)。
ループバックリダイレクト(RFC 8252、`http://127.0.0.1:PORT`への一時HTTPサーバー)を使うため、
WSL2のlocalhost自動転送によりWindows側の既定ブラウザでそのまま完結する。

## 予定を1件作成する

```bash
./gcal_event_add.sh 2026-08-25 09:00 09:30 00:30 "週次会議データの見直し（計画も報告も2週間分）"
```

`date` `start_hm` `end_hm` `reminder` `title`は省略できない(既定値は無い)。`title`は1つの
引数として渡す(空白を含む場合はクォートすること)。日時はローカルタイム(Asia/Tokyo)固定。

`reminder`は予定の何時間何分前に通知するかを`HH:MM`で指定する(例: 30分前なら`00:30`、
6時間前なら`06:00`)。通知不要なら`none`。カレンダーの既定通知(30分前)には頼らず、必ず
明示的に指定する設計。

`--dry-run`/`--confirm`は独立したオプション(`~/.claude/CLAUDE.md`参照):

- 既定(フラグ無し): 確認なしにそのまま登録する
- `--dry-run`: 内容をstderrに出すだけで、実際の登録はしない
- `--confirm`: `--dry-run`の有無と無関係に、登録の直前にstdinでy/nの確認を求める

```bash
./gcal_event_add.sh --dry-run 2026-08-25 09:00 09:30 00:30 "週次会議データの見直し（計画も報告も2週間分）"
./gcal_event_add.sh --confirm 2026-08-25 09:00 09:30 00:30 "週次会議データの見直し（計画も報告も2週間分）"
```

成功するとstdoutへ`id, date, start_hm, end_hm, title`のTSV1行を出力する(idは後で
`gcal_event_delete.sh`等に渡す)。

作成先カレンダーは`.env`の`GOOGLE_CALENDAR_ID`(既定`primary`=自分のメインカレンダー)。
別のカレンダーに登録したい場合はここを書き換える。

## 予定を1件削除する

```bash
./gcal_event_delete.sh jsi2rum5ph3kc5shmcrren57vc --confirm
```

`event_id`は`gcal_event_add.sh`が登録時にstdout/stderrへ出力する`id`をそのまま使う
(日時やタイトルでの曖昧検索はしない)。`--dry-run`/`--confirm`は`gcal_event_add.sh`と同じ。

## 予定を1件取得する(読み取り専用)

```bash
./gcal_event_get.sh jsi2rum5ph3kc5shmcrren57vc
```

`id, date, start_hm, end_hm, title, reminders, status`のTSV1行をstdoutへ出力する。

## 指定日の予定一覧を取得する(読み取り専用)

```bash
./gcal_event_list.sh TODAY tsv
./gcal_event_list.sh TOMORROW json
./gcal_event_list.sh 2026-08-25 tsv
```

`date`は`TODAY` `TOMORROW` `YYYY-MM-DD`のいずれか。出力形式は`json`か`tsv`を指定する
(既定値は無い)。取り消し済み(cancelled)の予定は除外する。各行/要素は
`id, date, time, title, reminders`(reminders配列は昇順)を持つ。

## 通知を1件追加・削除する

既存の予定の通知設定は`overrides`という配列で管理されており、他の通知を保持したまま
1件だけ追加・削除できる(全置き換えではない)。

```bash
./gcal_event_reminder_add.sh jsi2rum5ph3kc5shmcrren57vc 06:00 --confirm
./gcal_event_reminder_delete.sh jsi2rum5ph3kc5shmcrren57vc 06:00 --confirm
```

`reminder`は`gcal_event_add.sh`と同じ`HH:MM`形式(予定の何時間何分前か)。`--dry-run`/
`--confirm`も同じ。

## トークンの更新

各スクリプトは401を検知すると`refresh_access_token.py`経由で自動的にaccess_tokenを
更新するため、通常は手動での更新操作は不要。Googleのrefresh_tokenはfreeeと違い1回
使っても無効化されない(ローテーションしない)ため、再度`get_credentials.sh`を実行する
必要があるのはrefresh_token自体が失効・取り消しされた場合のみ。
