# due_watch — 使い方

（2026-10-15 改名: 旧名 async_comm。手段「非同期通信」ではなく目的「期限を見張る」で名付け直した。同日、Power Automate → Google Drive(`async_comm_teams`)経由の Teams 取り込みも廃止し、imc の Graph 取得に置き換えた(§5)。）

各通信手段（Gmail・Outlook・Teams）から「期限が迫っているメッセージ」だけを機械的に抽出し、
ローカルにキャッシュして一覧する仕組み。**設計根拠は `design.md`**（このファイルは手順書）。

## 現状（2026-10-15）

| 段 | 部品 | 状態 |
|---|---|---|
| lib | `due_watch_lib.py` | ✅ 実装済み |
| キャッシュ更新 | `due_watch_cache_update.sh` | ✅ 実装済み |
| キャッシュ表示 | `due_watch_cache_show.sh` | ✅ 実装済み |
| 取得（Teams） | imc（`~/imc`、別repo）が Graph API で取得 → `due_watch_fetch_teams.sh` が imc の保存分を読む | ✅ 2026-10-15 |
| 取得（Gmail/Outlook） | imc が Maildir に取得済み（gmail）。期限抽出の fetcher は未実装 | ⬜ |
| 定期実行 | `bin/cron/crontab`（`imc_fetch.sh mail/gmail/teams` と `due_watch_poll.sh`） | ✅ 2026-10-15 |

分担: **imc = 経路ごとの取得**（手動でも動く。定期実行を持たない）、**due_watch = 定期実行とキャッシュ・期限での一覧**。
Teams の流れ: `imc_fetch.sh teams`（cron :07系）→ imc の Maildir → `due_watch_fetch_teams.sh`（poll :00系）→ `cache_update` → `cache_show`。
（2026-09-08〜10-15 は Power Automate → Google Drive(G:) 経由だった。G: が外れると気づかれずに止まるため廃止。フローも削除。）

---

## 初回の通しテスト（コア部分、手動）

`date -d`（GNU date, WSL標準）で期限を「今日基準」にしているので、いつ実行してもバケットが同じになる。

### Step 0. 場所

```bash
cd ~/bin/due_watch
```

### Step 1. サンプルの交換形式JSONを作る

```bash
cat > /tmp/ac_sample.json <<EOF
[
  {"source":"teams","id":"t1","summary":"9/1ランチ会 出欠の返信期限(今朝で切れ)","deadline":"$(date -d 'today 08:00' +%Y-%m-%dT%H:%M:%S%:z)","url":null,"posted_at":"$(date -d 'yesterday 18:00' +%Y-%m-%dT%H:%M:%S%:z)","addressed_to_me":true},
  {"source":"teams","id":"t2","summary":"週次会議 明日14時に順延(末広くん通院)","deadline":"$(date -d 'tomorrow 14:00' +%Y-%m-%dT%H:%M:%S%:z)","url":"https://teams.microsoft.com/l/message/xxx","posted_at":"$(date +%Y-%m-%dT%H:%M:%S%:z)","addressed_to_me":false},
  {"source":"gmail","id":"g1","summary":"経費精算 今月分の締め","deadline":"$(date -d 'today +10 days 18:00' +%Y-%m-%dT%H:%M:%S%:z)","url":"https://mail.google.com/x","posted_at":"$(date +%Y-%m-%dT%H:%M:%S%:z)","addressed_to_me":false},
  {"source":"gmail","id":"g2","summary":"就業規則改定の周知(要確認・期限なし)","deadline":null,"url":"https://mail.google.com/y","posted_at":"$(date +%Y-%m-%dT%H:%M:%S%:z)","addressed_to_me":false},
  {"source":"outlook","id":"o1","summary":"年末調整の案内","deadline":"$(date -d 'today +90 days 09:00' +%Y-%m-%dT%H:%M:%S%:z)","url":null,"posted_at":"$(date +%Y-%m-%dT%H:%M:%S%:z)","addressed_to_me":false}
]
EOF
cat /tmp/ac_sample.json
```

### Step 2. キャッシュへ差分マージ

```bash
./due_watch_cache_update.sh < /tmp/ac_sample.json
```

期待（stderr）:

```
due_watch_cache_update.py: gmail, outlook, teams: 入力5件 => upsert / 消滅除去0 / 期限切れ除去0 => キャッシュ5件 (...)
次にすべきこと: due_watch_cache_show.sh tsv で一覧を確認してください
```

### Step 3. 一覧表示

```bash
./due_watch_cache_show.sh tsv
```

期待（posted_at / addressed_to_me / deadline_bucket / deadline / source / summary / url。同一bucket内はposted_at降順）:

```
<昨日18:00>   true   今       <今朝の時刻>      teams   9/1ランチ会 出欠の返信期限(今朝で切れ)   -
<今の時刻>    false  今日+1   <明日14:00>       teams   週次会議 明日14時に順延(末広くん通院)   https://teams.microsoft.com/l/message/xxx
<今の時刻>    false  来月末   <+10日 18:00>     gmail   経費精算 今月分の締め                    https://mail.google.com/x
<今の時刻>    false  それ以降 <+90日 09:00>     outlook 年末調整の案内                          -
<今の時刻>    false  なし     -                gmail   就業規則改定の周知(要確認・期限なし)     https://mail.google.com/y
```

JSON でも見られる:

```bash
./due_watch_cache_show.sh json
```

### Step 4. 差分マージの挙動を確認

teams だけを再取得したとき（`t1` は対応済みで消え、`t2` の時刻が変わり、期限切れの `t9` が来た）を模擬:

```bash
cat > /tmp/ac_sample2.json <<EOF
[
  {"source":"teams","id":"t2","summary":"週次会議 14:30に微修正","deadline":"$(date -d 'tomorrow 14:30' +%Y-%m-%dT%H:%M:%S%:z)","url":"https://teams.microsoft.com/l/message/xxx","posted_at":"$(date +%Y-%m-%dT%H:%M:%S%:z)","addressed_to_me":false},
  {"source":"teams","id":"t9","summary":"古い依頼(期限3日前)","deadline":"$(date -d 'today -3 days 12:00' +%Y-%m-%dT%H:%M:%S%:z)","url":null,"posted_at":"$(date +%Y-%m-%dT%H:%M:%S%:z)","addressed_to_me":false}
]
EOF
./due_watch_cache_update.sh < /tmp/ac_sample2.json
./due_watch_cache_show.sh tsv
```

確認ポイント:

- `teams/t1` が消えている（入力に無い teams レコード ⇒ 消滅除去）
- `teams/t2` の summary が「14:30に微修正」、deadline が明日14:30 に更新
- `teams/t9` は出てこない（期限が1日以上前 ⇒ 期限切れ除去。stderr に「期限切れ除去1」）
- **`gmail/g1`, `gmail/g2`, `outlook/o1` はそのまま残っている**（入力に含まれない source は触らない）

### Step 5. キャッシュの中身を直接見る

```bash
cat _cache.json
```

各レコードに `first_seen`（最初にキャッシュへ入った時刻）と `last_seen`（poll が最後に見た時刻）が付く。
Step 2 と Step 4 を数秒以上あけて実行していれば、`t2` の `first_seen` は Step 2 の時刻のまま、
`last_seen` だけ Step 4 の時刻に更新されている（同じ秒に実行すると同値になるだけ）。

### Step 6. 異常系（弾かれることの確認）

```bash
echo '[{"source":"slack","id":"1","summary":"x","deadline":null,"url":null,"posted_at":null,"addressed_to_me":false}]' | ./due_watch_cache_update.sh   # source不正 => exit 1
echo '[{"source":"teams","id":"1","summary":"x"}]'                            | ./due_watch_cache_update.sh   # 必須キー欠損 => exit 1
echo '[{"source":"teams","id":"1","summary":"x","deadline":"来週","url":null,"posted_at":null,"addressed_to_me":false}]'| ./due_watch_cache_update.sh   # deadline形式不正 => exit 1
echo '{}'                                                                     | ./due_watch_cache_update.sh   # 配列でない => exit 1
echo '[]' | ./due_watch_cache_update.sh   # OK。期限切れ掃除だけ走り、既存は消えない
./due_watch_cache_show.sh xml   # 引数不正 => usage + exit 1
```

いずれも `_cache.json` は壊れない（不正入力時は書き込まない）。

### Step 7. 後片付け

```bash
rm -f _cache.json /tmp/ac_sample.json /tmp/ac_sample2.json
```

`_cache.json` は `.gitignore` 対象（`_*`）なのでコミットされることはないが、
テストデータを実キャッシュの場所に残すと本番 poll と混ざるので消しておく。

---

## セットアップ

```bash
cd ~/bin/due_watch
./initialize.sh
```

検査だけで何も書き換えない（冪等）: python3、imc の有無と Teams ログイン、
`teams_channels.local.tsv` のチャネルを imc も取得しているか、`due_watch_fetch_teams.sh` のスモークテスト。

取り込む Teams チャネルを増やすとき:

1. `teams_channels.local.tsv` に `team<TAB>channel` を足す（名前は `~/imc/imc_teams_channel_list.sh tsv` の1・2列目）
2. 同じ行を `~/imc/teams_channels.local.tsv` にも足し、`~/imc/imc_teams_fetch.sh <7日前の日付> < その行` で一度取得する
3. `./initialize.sh` で確認

### 定期実行（cron）を有効化する

```bash
~/bin/cron/cron_register.sh --dry-run    # 差分確認（登録しない）
~/bin/cron/cron_register.sh --confirm    # user crontab を bin/cron/crontab で全置換（y/n あり）
crontab -l                               # 確認
```

`bin/cron/crontab` に `due_watch_poll.sh`（:00系）と `imc_fetch.sh mail/gmail/teams`（:03/:05/:07系）が入っている
（2026-10-15 登録済み）。ログは `~/bin/due_watch/_poll.log`、`_fetch_{mail,gmail,teams}.log`。

---

## 次段階

1. `due_watch_fetch_gmail.sh`: imc の Maildir（gmail）から期限のあるものを抽出 → `due_watch_poll.sh` の `FETCHERS` に追加
2. `deadline_bucket` が `今`/`今日` に上がったときの通知（未設計）
3. Teams: 1:1・グループチャット（imc 側の新経路）／@メンション（`addressed_to_me`）での絞り込み

詳細は `design.md` §4〜§7。

---

## ファイル

| ファイル | 役割 | git |
|---|---|---|
| `initialize.sh` | セットアップの検査（imc・ログイン・チャネル・スモークテスト、冪等） | 追跡 |
| `due_watch_poll.sh` | fetch 群 → 連結 → `cache_update`（cron から10分毎） | 追跡 |
| `due_watch_fetch_teams.sh` / `.py` | imc が保存した Teams メッセージ → 交換形式 | 追跡 |
| `teams_channels.local.tsv` | 期限の一覧に取り込む Teams チャネル（チーム・チャネル名は勤務先が分かるため） | gitignore（`.local.`） |
| `teams_channels.local.tsv.template` | 上記のコピー元 | 追跡 |
| `due_watch_lib.py` | 共有モジュール（import 専用、単体実行しない） | 追跡 |
| `due_watch_cache_update.sh` / `.py` | 交換形式(stdin) ⇒ `_cache.json` 差分マージ | 追跡 |
| `due_watch_cache_show.sh` / `.py` | `_cache.json` ⇒ deadline順の一覧（tsv/json） | 追跡 |
| `_cache.json` | キャッシュ（二次情報、SSoTから再生成可能） | gitignore（`_*`） |
| `design.md` | 設計根拠（なぜ） | 追跡 |
| `readme.md` | このファイル（どうやって） | 追跡 |
