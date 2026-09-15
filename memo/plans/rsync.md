# home ⇔ office 同期構想 (rsync)

## 状態

検討案。未実装。採用済み仕様ではない。

`memo/structured.md` の `# SYNC` セクションを起点に、構想を書き起こしたもの。
実装前に「何を同期するのか(対象集合)」「どちらが SSoT か」「方向ごとの安全策」を
決める必要がある。

## 目的

2 つのリポジトリの間で、**共通の部品(スクリプト類)** を同期し、
一方で得た改善をもう一方へ反映できる状態にする。

| | Home | Office |
|---|---|---|
| リモート | `git@github.com:takamitsu-ishioka/home-ide-developer.git` | `github.com/dominosoft-org/integrated-work-environment` |
| 所有 | takamitsu-ishioka (個人) | dominosoft-org (会社) |
| 公開範囲 | **public** | **private** |
| 目的 | linux CLI による統合開発環境の開発 | 同じ |
| 対象・環境・制約 | 個人・WSL・公開可 | 会社・社内環境・機密あり |

- 目的は同じ。対象と環境と制約は別。
- `bin/` 配下を中心に共通の部品が相当数ある。

## 非目標

次は同期しない(意味が両環境で異なる、または同期が事故を生む)。

- `CLAUDE.md` / `CLAUDE.en.md` — 憲法。制約が両環境で異なりうる。
- `.env` / `.env.*` — 機密情報。既に `.gitignore` 済み。
- `.home-ide-developer/environment_name` ほかマシン固有の状態ファイル。
- 独立サブリポジトリ (`/ghost/`, `/mmwave/`, `/note-article-manager/` など)。
  片方にしか無い、あるいは中身が違う。
- リモート URL・パス・所有者に依存する設定。
- `bin.tgz`, `openapi-generator-cli.jar` などの巨大生成物。
- 各ツール (Claude Code / Codex) のキャッシュ・履歴・認証。

「共通化できるもの」ではなく「同期せざるを得ないもの」だけを対象にする。

## やりたいこと

1. **office → home** : Office 側の改善を Home へ取り込む。
2. **home → office** : Home 側の改善を Office へ取り込む。
   (Office 側で作業しないと push できないため、Home 単独では完結しない見込み。)

## 問題点

### 1. 単純なコピーはできない

同期対象と非対象がディレクトリ内に混在している。ファイル単位・
場合によっては行単位で「共通部分」と「環境固有部分」が分かれる。

### 2. private → public の情報漏洩リスク (最重要)

`office (private/会社)` → `home (public/個人)` の向きは、
機密が公開リポジトリへ漏れる事故になりうる。

→ **denylist(除外指定)ではなく allowlist(同期するものを明示列挙)** で運用する。
   「除外し忘れ」は事故るが、「列挙し忘れ」は単に同期されないだけで安全側に倒れる。

### 3. どちらが SSoT か決まっていない

共通部品について、Home と Office のどちらが正か。
ファイルごとに正の側が異なる可能性がある(例: freee 連携は Home 発、
社内 CI 連携は Office 発)。

### 4. rsync は git 履歴を運ばない

タイトルは rsync だが、rsync はワーキングツリー間の同期であり、
どちらの git 履歴も混ざらない/引き継がれない。
「誰がいつなぜ変えたか」は同期の瞬間に失われる。

## 選択肢

### A. rsync + 同期マニフェスト (allowlist)

同期対象を列挙したファイル (`sync_manifest.txt` 等) を両リポジトリに置き、
`rsync --files-from=sync_manifest.txt` で一方向ずつ流す。

- ⭕ 実装が薄い。UNIX 哲学に合う。DJC 的に「差分を人間が見る」運用と相性が良い。
- ⭕ allowlist を明示できる。
- ❌ git 履歴が運ばれない。コンフリクト検出は「同期前後の diff を見る」手動運用。
- ❌ マニフェストの二重管理(両リポジトリで一致させる必要)。

### B. 共通部品を第 3 のリポジトリへ分離

`bin/` の共通スクリプトを `dev-env-common` (仮) として切り出し、
Home / Office の双方が git submodule または subtree で取り込む。

- ⭕ SSoT が 1 箇所に定まる。履歴も残る。
- ❌ 分離のコストが大きい。どれが「共通」かを事前に確定させる必要
   (= 「共通化せざるを得ないものを共通化せよ」の判断を前倒しで強制される)。
- ❌ submodule の運用は WSL・CI で嵌りやすい。

### C. git remote 相互登録 + format-patch / cherry-pick

Home のクローンに Office を remote 追加し、対象ファイルの変更を
`git format-patch` → `git am` で選択的に移送。

- ⭕ 履歴(コミットメッセージ)が残る。
- ❌ private リモートへのアクセスを Home 環境に持ち込む必要。漏洩面が増える。
- ❌ ディレクトリ構造が両者で違うと patch が当たらない。

### D. 手動コピー (現状)

- ⭕ ゼロ実装。
- ❌ 属人的。同期漏れ・逆流(古い版で上書き)が起きる。

## 当面の方針 (案・要確認)

1. まず **同期対象集合を確定** する。`bin/` を 1 ファイルずつ棚卸しし、
   `common` / `home-only` / `office-only` のいずれかにタグ付けする。
2. 対象集合が小さく安定しているなら **選択肢 A (rsync + allowlist)** で開始。
   大きく増え続けるなら **選択肢 B** を検討。
3. 方向ごとに別スクリプトにする (責務分離):
   - `dev_env_sync_office_to_home.sh`
   - `dev_env_sync_home_to_office.sh`
   - どちらも `--dry-run` / `--confirm` 対応。副作用前に入出力諸元を表示。
4. DJC: 同期後、両側の対象ファイルの diff が空になることを収束条件とする。
   diff が出たら人間が差分だけ調査。

## 未決事項 (設計者に確認)

- 共通部品の SSoT はファイル単位で決めるのか、リポジトリ単位で一律に決めるのか。
- Office 側リポジトリのディレクトリ構造は Home と一致しているか。
- Office 環境から Home の public リポジトリへ push する運用は許容されるか
  (会社ポリシー)。
- この同期を自動(cron 等)で回すのか、手動トリガーのみか。
