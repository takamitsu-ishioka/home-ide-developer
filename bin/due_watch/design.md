# due_watch 設計書

（2026-10-15 改名: 旧名 async_comm。手段「非同期通信」ではなく目的「期限を見張る」で名付け直した。同日、Power Automate → Google Drive(`async_comm_teams`)経由の Teams 取り込みも廃止し、imc の Graph 取得に置き換えた(§5)。）

出典：`/home/developer/projects/index.md`「開発環境の開発 > 通信の非同期化」。

## 目的

「必要な時に必要な情報を得る」。メール（Gmail/Outlook）やメッセージングアプリ（Teams）の通知が届いた瞬間に人間が同期的に反応する、という運用を前提にしない。

動機となった具体例：Teamsのリマインダーメッセージ（例：「9/1ランチ会出欠の返信期限が本日」）本文には、返信対象である元の招待そのものへの直リンクが含まれておらず、都度Teams UIを探索する認知負荷が発生した。この種の「期限が迫っている」通知だけを各通信手段から機械的に抽出し、ローカルにキャッシュ・一覧表示することで、探索コストをゼロに近づける。

## アーキテクチャ：SSoT・交換形式・パイプライン

- **SSoT**: 各通信手段（Gmail・Outlook・Teams）側に既に存在するメール・予定・メッセージそのもの。人間もAIも書き換えない一次情報。
- **二次情報（キャッシュ）**: `bin/due_watch/_cache.json`。SSoTから都度再生成可能なため、CLAUDE.mdの規約に従い`_`接頭辞を付け`.gitignore`対象とする。
- **交換形式（fetchスクリプトの出力）**: JSON配列。1メッセージ（または1予定・1招待）につき1レコード。

  | フィールド | 内容 |
  |---|---|
  | `source` | `gmail` \| `outlook` \| `teams` |
  | `id` | 発信元システムでの一意識別子（文字列） |
  | `summary` | 件名・要約（1行想定） |
  | `deadline` | 期限日時（ISO8601, Asia/Tokyo）。無ければ`null` |
  | `url` | 元メッセージ・招待への深いリンク。取得できなければ`null` |
  | `posted_at` | 投稿・作成日時（ISO8601, Asia/Tokyo）。取得できなければ`null`（2026-09-15追加） |
  | `addressed_to_me` | 自分宛と判定できたか。bool（取得できなければ`false`、2026-09-15追加） |

  fetchスクリプトが出すのはこの7フィールドだけ。`deadline_bucket`（時間相対なので保存しない。表示時に算出）や `first_seen`/`last_seen`（キャッシュの台帳項目）は下流が付ける。

- **キャッシュのレコード**: 交換形式の7フィールド + `first_seen`（この message を最初にキャッシュへ入れた時刻）+ `last_seen`（poll が最後にこの message を見た時刻）。

- **パイプライン**:
  ```
  SSoT(各通信手段) => source別取得スクリプト => 交換形式(JSON配列) => cache_update(差分マージ) => _cache.json => cache_show(deadline順に一覧)
  ```

## 設計方針

CLAUDE.mdの方針（[[feedback_ai_as_parts_maker]]）に従い、AIが毎回APIを呼ぶのではなく、取得・キャッシュ更新・表示をそれぞれ決定論的なスクリプトとして部品化する。「期限が迫っているかどうか」の判定自体は`deadline`の値からの機械的な計算（決定論的）だが、本文から`deadline`を抽出する処理（特にTeamsの自然文）は決定論的な機械化が難しく、AIの判断を要する可能性がある（下記「未決事項」参照）。

## 全体設計

パイプラインの段:

| # | 部品 | 状態 |
|---|---|---|
| 1 | 共有モジュール `due_watch_lib.py`（交換形式の検証、`deadline_bucket` 算出、`_cache.json` 読み書き） | 実装済み 2026-09-08 |
| 2 | `due_watch_cache_update.sh`（交換形式 stdin → `_cache.json` 差分マージ） | 実装済み 2026-09-08 |
| 3 | `due_watch_cache_show.sh`（`_cache.json` → deadline順の一覧） | 実装済み 2026-09-08 |
| 4 | `due_watch_fetch_{gmail,outlook}.sh`（OAuth、メール取得 → 交換形式） | 未実装 |
| 5 | `due_watch_fetch_teams.sh`（imc が保存した Teams メッセージ → 交換形式） | 実装済み 2026-10-15（2026-09-08 版は Power Automate 経由、廃止） |
| 6 | `due_watch_poll.sh`（5 を呼んで 2 へ流すオーケストレータ、cron から10分毎） | 実装済み 2026-09-08 |
| 6' | `bin/cron/crontab` の登録行（poll と imc_fetch.sh mail/gmail/teams） | 登録済み 2026-10-15 |
| 7 | `initialize.sh`（準備の検査を1コマンドに） | 実装済み 2026-10-15 改訂 |

### 2. キャッシュ更新スクリプト（実装済み、2026-09-08）

`due_watch_cache_update.sh` / `.py`：交換形式JSON配列を**stdin**で受け取り、`_cache.json`へ差分マージする（取得スクリプトの呼び出しは `due_watch_poll.sh` の役目。分離）。

マージ規則:

- key = `(source, id)`。入力にあれば **upsert**（`summary`/`deadline`/`url` を更新、`last_seen` を now、`first_seen` は保持）。無ければ新規追加（`first_seen`=`last_seen`=now）。
- **消滅除去**: 入力に含まれる `source` について、入力に無いキャッシュレコードは「対応済み・削除された」とみなして除去する。入力に**含まれない** `source` のレコードは触らない（その source の fetch を今回回していないだけかもしれない）。→ `due_watch_cache_update.sh` に空配列 `[]` を渡すと「期限切れ除去」だけ走り、既存は消えない。
- **期限切れ除去**: `deadline` が now より `EXPIRE_GRACE`（既定1日、`due_watch_cache_update.py` の定数）以上前のレコードは除去。

### 3. キャッシュ表示スクリプト（実装済み、2026-09-08／ソート・列2026-09-15更新）

`due_watch_cache_show.sh <tsv|json>` / `.py`：`_cache.json` を読み、`deadline_bucket` → `deadline` 順（主キー、期限が近い順）→ 同一 `(deadline_bucket, deadline)` 内は `posted_at` の新しい順（副キー）にソートして出力する読み取り専用スクリプト。`deadline_bucket` は保存値ではなく**実行時の now を基準にその場で算出**する。TSV列: `posted_at`, `addressed_to_me`, `deadline_bucket`, `deadline`, `source`, `summary`, `url`。

- 主キーを`deadline_bucket`/`deadline`のまま残したのは設計判断：現状`deadline`を持つのは今のところ0件（Teamsは§5参照で`null`運用）なので実質的には全件`posted_at`降順に見えるが、将来gmail/outlookが`deadline`を持つレコードを流し始めたら「期限が近い順」という本来の目的（§目的）が壊れないようにするため。ユーザー要望は「posted_atの降順」だったが、この解釈で実装した（要望と異なる場合は指摘してください）。

### 3.1 `deadline_bucket` の算出基準（`due_watch_lib.deadline_bucket`、2026-09-08）

暦日境界は JST。`IMMINENT` は `due_watch_lib.py` の定数（既定3時間、調整可）。

| バケット | 条件 |
|---|---|
| `なし` | `deadline` が `null` |
| `今` | 期限切れ、または `now + IMMINENT` 以内 |
| `今日` | 今日中（暦日）で、`今` ではない |
| `今日+1`〜`今日+6` | N日後 |
| `来月末` | +7日以降で、翌月末（`YYYY-MM-末日 23:59:59`）までに収まる |
| `それ以降` | それより先（design.md 初版の列挙に無かった遠い側の受け皿） |

### 4. source別取得スクリプト（未実装、`bin/gcal`/`bin/freee` と同じ OAuth パターン）

`due_watch_fetch_gmail.sh` / `due_watch_fetch_outlook.sh` — Gmail API / Microsoft Graph（メール）。認証は `bin/gcal` と同様の OAuth Desktop app クライアントで実現できる見込み（未検証）。

`due_watch_fetch_teams.sh` — §5参照。メールも同じく imc が Maildir に取得済みなので、gmail/outlook も「imc の保存分を読む」形にするのが第一候補（2026-10-15）。

### 5. Teams の取り込み — imc の保存分を読む（2026-10-15）

**分担**: 取得は imc（`~/imc`、別repo・公開）、due_watch はその結果を読んでキャッシュするだけ。
imc は経路ごとの取得（`imc_fetch.sh <mail|gmail|teams|all>`、手動でも動く、定期実行を持たない）。
定期実行は due_watch 側の `bin/cron/crontab`。依存は due_watch → imc の CLI の一方向（imc は呼び出し側を知らない）。

```
cron :07系  imc_fetch.sh teams   … Graph API(ChannelMessage.Read.All、委任、2026-10-15 管理者同意済み)
            → ~/imc/_var/maildir/teams-<チャネルhash>/ に1メッセージ1ファイル → notmuch
cron :00系  due_watch_poll.sh → due_watch_fetch_teams.sh
            → imc_mail_list.sh 'folder:/teams-.*/ and date:<7日前>..' json の path を読む
            → teams_channels.local.tsv のチャネルだけ → 交換形式 → cache_update
```

- **imc との契約**（imc の公開出力だけ）: `imc_mail_list.sh` の `path`（`~/imc/_var/maildir` からの相対）、
  1メッセージ1ファイルのヘッダ `X-Imc-Team` / `X-Imc-Channel` / `X-Imc-Addressed-To-Me`、本文 = 投稿本文 + 空行 + Teams のリンク。
- **`id`**: imc の Message-ID のローカル部 `<メッセージid>.<チャネルhash>`。Teams のメッセージ id は作成時刻のミリ秒なので、チャネルをまたぐと衝突しうる。
- **`url`**: Graph API が返す webUrl（以前のように `.env` の固定値から合成しなくてよい）。
- **`addressed_to_me`**: Graph のメンション構造で判定した値（以前は本文にログイン名が含まれるかのフォールバック）。
- **`deadline`**: 当面 `null`（自然文からの抽出は決定論では難しい。従来どおり）。
- **鮮度**: 直近7日（`MAX_AGE_DAYS`、コード内の定数）。
- **チャネルを増やす**: `teams_channels.local.tsv` と `~/imc/teams_channels.local.tsv` の両方に行を足す（`initialize.sh` が食い違いを検出）。

#### 廃止した方式: Power Automate → Google Drive（2026-09-08〜10-15）

当時は Graph API の `ChannelMessage.Read.All` に管理者同意が無かったため、Power Automate のフロー
（「チャネルに新しいメッセージが追加されたとき」、社内FIG 固定）が1メッセージ1 JSON を Google Drive に書き、
G: ドライブ経由で読んでいた。廃止理由: ①G: のマウントが外れると気づかれずに止まる（9月以降 poll の失敗 111 回、
2026-10-15 も 14:02 から停止）②1フロー=1チャネル ③リンクを `.env` の固定値から合成する必要 ④部品が多い
（フロー・Drive・同期アプリ・マウント）。2026-10-15 に管理者同意が得られ、imc の Graph 取得に置き換えた。
フローは削除。詳細は git の履歴（このファイルの 2026-10-15 以前）。

### 6. オーケストレータ（実装済み、2026-09-08）

`due_watch_poll.sh`：`FETCHERS` 配列の fetch スクリプトを順に実行し、成功した出力（交換形式JSON配列）を1つに連結して `due_watch_cache_update.sh` へ渡す。cron から `cron_run.sh` 経由で10分毎に叩く（`bin/cron/crontab` に登録行あり、登録は `cron_register.sh --confirm` で人間が実行）。非対話。副作用は `_cache.json` の更新のみ。

- **fetch が失敗（exit≠0）した source は今回スキップ**する。失敗を「空」として `cache_update` へ渡すと、その source の既存レコードが全部「消滅除去」されるため。fetch が成功して 0 件（`[]`）なら正当な「案件なし」として通す。
- 現在 `FETCHERS` は `due_watch_fetch_teams.sh` のみ。gmail/outlook ができたら足す。
- `bin/cron/crontab`: `due_watch_poll.sh`（:00系）と、その前段の `imc_fetch.sh mail/gmail/teams`（:03/:05/:07系）。`cron.env` の `PATH` に `$HOME/bin/due_watch` を含めてある。

### 7. `initialize.sh`（2026-10-15 改訂）— 準備の検査

検査だけで何も書き換えない: python3 → imc の有無と Teams ログイン（`imc_teams_auth.sh status`）→
`teams_channels.local.tsv` のチャネルを imc も取得しているか → `due_watch_fetch_teams.sh` のスモークテスト。
NG なら「次にすべきこと」を出して止まる。以前の Power Automate フロー作成の人間 wait 段（chrome.sh で開き、
sink に JSON が現れるのを検証）は方式の廃止とともに削除した。

## 未決事項

- **Gmail/Outlook の認証方式・スコープ**：`bin/gcal` と同様の OAuth Desktop app クライアントで実現できる見込みだが未検証（`initialize.sh` にも同種の人間 wait 段を足す）。
- **`deadline` 自然文抽出**（§5。当面 `null` 運用）。
- **通知**：`deadline_bucket` が `今`/`今日` に上がった瞬間に 何で知らせるか未設計（勤怠連絡への Webhook 投稿は返信ができないため 2026-10-15 に廃止。通知は imc の ntfy 等を検討）。

## 動機事例

- **2026-09-08**: 牧田さんから Teams で「末広くん通院のため週次会議を明日14時に変更、やりとりは担当者間で」。カレンダー登録直後だったので手で `gcal_event_delete` + `gcal_event_add` し直した。この「Teams の1メッセージ → 予定の変更」は、poll → 要約 → 変更案ドラフト → 人間が承認、という due_watch + CLAUDE.md「非同期処理モデル（人間を待つ）」の典型。共有予定の書き換えなので承認は外せない（全自動にはならない）が、「Teams UI を探索して手で直す」認知負荷は消える。
- Teams リマインダー「9/1ランチ会出欠 返信期限本日」に元招待への直リンクが無く毎回 UI 探索、が当初の動機（§目的）。
