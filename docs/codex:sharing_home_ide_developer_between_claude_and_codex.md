# `.home-ide-developer` をClaude CodeとCodexで共有する設計案

## 状態

この文書は検討案であり、未実装である。

採用済み仕様ではない。実装前に、共有する状態の意味、同時セッション時の扱い、Codex側の接続方法を決定する必要がある。

## 目的

Claude CodeとCodexが、同じPC上の次の情報を同じ意味で利用できるようにする。

- 実行環境名
- ホストとホームIDEの識別
- ユーザーが現在注目しているrepository
- repositoryのローカルパス、branch、remote
- 安全な操作判断に必要なmachine-local文脈

目標はClaude CodeとCodexの内部設定を統合することではない。両者が参照する、製品非依存の環境状態を定義することである。

## 非目標

次は共通化しない。

- モデル選択
- sandboxまたは権限設定
- trust設定
- UIテーマとキーバインド
- Claude Codeのhook定義
- Codex固有の設定
- 会話履歴
- 認証情報
- 各製品のキャッシュと内部DB
- CodexやClaudeのセッション表示名

「共通化できるもの」ではなく、「意味を一つにせざるを得ないもの」だけを共通化する。

## 設計原則

### 1. `.home-ide-developer` は製品非依存とする

`.home-ide-developer` のファイル形式に、Claude CodeまたはCodexのhook固有形式を保存しない。

```text
悪い依存:
.home-ide-developer/current_repo
    └── ClaudeのhookSpecificOutputを保存

望ましい依存:
.home-ide-developer/current_repo
    └── 中立なrepository情報を保存
          ├── Claude用アダプターが変換
          └── Codex用アダプターが変換
```

### 2. 共通状態と製品固有アダプターを分離する

```text
                         ┌── ~/.claude/ + Claude hook
.home-ide-developer ─────┤
                         └── ~/.codex/ + Codex接続手段
```

`.claude/` と `.codex/` は統合しない。双方が同じ共通コマンドまたはデータ契約を利用する。

### 3. machine-local状態はGitで共有しない

home PCとoffice PCは別の開発環境インスタンスである。

共通設計はGitで共有するが、次は各PCに固有とする。

- `environment_name`
- `current_repo`
- ローカル絶対パス
- セッション状態
- 認証情報

office PCにのみ存在するrepositoryのパスを、home PCの状態へ同期してはならない。

### 4. ファイルパスを利用者へ漏らしすぎない

Claude用、Codex用、人間用の各処理が、状態ファイルの配置とJSON構造を個別に実装すると、配置変更時に不整合が発生する。

状態へのアクセスは将来的に共通コマンドへ集約することが望ましい。

仮称:

```bash
home_ide_context_get.sh json
home_ide_current_repo_get.sh json
home_ide_current_repo_set.sh
```

名称と入出力は未決定である。

## 現在の共通化可能性

### `environment_name`

共有に適している。

値は `LOCAL|ALPHA|BETA|PROD` であり、Claude CodeとCodexが別々に解釈すべき情報ではない。

ただし現状、実体の配置と `whereami.py` の参照先に不整合がある。共通化前にSSoTへのアクセス経路を一つにする必要がある。

### `current_repo`

データ自体は共有に適している。

現在の例:

```json
{
  "path": "/home/developer/example-repository",
  "name": "example-repository",
  "branch": "main",
  "remote_url": "git@example.invalid:owner/example-repository.git"
}
```

この形式は特定のAI製品に依存していない。

一方、現在の更新・通知スクリプトはClaude Code中心である。

- `current_repo_set.sh`: 共通化可能な書き込み処理
- `bin/claude/claude_current_repo_announce.sh`: Claude Code用アダプター(SessionStartフック)
- `bin/claude/claude_statusline.sh`: Claude Code用UIアダプター(statusLineフック。副次的にrate_limitsもキャッシュする)

Codex用には、同じデータをCodexが利用できる文脈へ変換する別アダプターが必要になる。

## 推奨アーキテクチャ

```text
                       machine-local state
                  .home-ide-developer/
                  ├── environment_name
                  └── current_repo
                            |
                    common context commands
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v
     Claude adapter     Codex adapter       human CLI
     SessionStart       start/context       whereami
     statusLine         available UI        status command
```

共通コマンドは中立なJSONまたはTSVをstdoutへ出す。各製品固有アダプターは、それを製品固有形式へ変換するだけとする。

## `current_repo` の意味に関する選択

最大の設計判断は、`current_repo` が誰に属するかである。

### 案A: PC全体で一つの共通フォーカス

`current_repo` を「このPCでユーザーが現在注目しているrepository」と定義する。

利点:

- 概念が単純
- ClaudeからCodexへ作業対象を引き継げる
- セッションをまたいで状態を保持できる
- 現在の実装をほぼ維持できる

欠点:

- 複数セッションが同時に別repositoryを扱うと最後の更新が勝つ
- バックグラウンドagentが書き換えると、人間の意図とずれる可能性がある

### 案B: エージェントのセッションごとに保持

```text
.home-ide-developer/
├── current_repo
└── sessions/
    ├── claude/<session-id>.json
    └── codex/<thread-id>.json
```

`current_repo` はPC全体のデフォルトとし、開始後はセッション別のスナップショットを利用する。

利点:

- 並行作業が競合しない
- セッションごとの対象が明確

欠点:

- セッションIDとライフサイクル管理が必要
- 古い状態の清掃が必要
- 製品固有概念が共通状態へ入りやすい
- 現状に対して複雑すぎる可能性がある

### 暫定推奨

最初は案Aを採用する。

ただし、`current_repo` をAIが暗黙に頻繁に書き換えるのではなく、人間の明示操作または明確なワークフローだけが更新する状態として扱う。

実際に同時セッション競合が発生した時点で、案Bを追加する。この判断は「共通化せざるを得ないものだけを共通化する」という既存原則に沿う。

## 読み取りと書き込みの権限

推奨規則:

| 主体 | 読み取り | 書き込み |
|---|---:|---:|
| 人間 | 可 | 可 |
| Claude Code | 可 | 明示された操作のみ |
| Codex | 可 | 明示された操作のみ |
| background agent | 可 | 原則不可 |

AIセッションの起動だけで `current_repo` を書き換えてはならない。cwdや直前に触ったrepositoryから暗黙に推定して上書きすると、「ユーザーが注目している対象」という意味が失われる。

## データ契約の改善候補

将来、`current_repo` に次のフィールドを追加する余地がある。

```json
{
  "schema_version": 1,
  "path": "/home/developer/example-repository",
  "name": "example-repository",
  "branch": "main",
  "remote_url": "git@example.invalid:owner/example-repository.git",
  "updated_at": "2026-01-01T00:00:00+09:00",
  "updated_by": "human"
}
```

ただし、現時点で必要性が確認されていないフィールドは追加しない。

特にbranchは時間とともに変わるため、SSoTではなく保存時点のスナップショットである。利用時には実際のGit状態と比較し、差があれば古い情報として扱う必要がある。

## Codexへの接続方法

Claude CodeではSessionStart hookとstatusLineが既に利用されている。

Codexで同等のhookまたはUI拡張が利用できるかは、この文書では確定していない。仕様書に記載なし。現時点では推測を避け、次の接続候補だけを挙げる。

1. Codex起動前に共通contextを取得するラッパー
2. Codexが読む永続指示から共通contextコマンドの利用を指示
3. Codexに正式な起動hookが存在する場合は、そのhook用アダプター
4. ユーザーが必要時にcontextコマンドを実行して提示

採用前に、現在利用しているCodexバージョンの公式仕様と実際の挙動を確認する。

Codex右下のセッション名は、Git repository名、branch、worktree、`current_repo` とは別概念である。共通contextを渡せても、その表示を変更できるとは限らない。

## 競合と整合性

共通状態を複数プロセスが扱う場合、次を検討する。

- 書き込み途中のJSONを他プロセスが読まないこと
- 同時更新時のlast-writer-winsを許容するか
- 存在しないローカルパスをどう扱うか
- branchとremoteが保存時点から変わった場合の扱い
- home PCとoffice PCの状態を誤ってGit同期しないこと
- `.home-ide-developer` のディレクトリ名変更後も参照できること

実装する場合、書き込みは一時ファイルを作成してから同一ファイルシステム上でrenameする原子的更新が望ましい。

## 段階的な実装案

この節も未実装案である。

### Phase 1: 契約を確定

- `.home-ide-developer` を製品非依存状態の置き場と明記
- `current_repo` の意味をPC全体の共通フォーカスと定義
- 読み取り・書き込み主体を定義

### Phase 2: 共通アクセスを作る

- environmentの読み取りを一か所に集約
- current repositoryの読み書きを一か所に集約
- 既存のClaude用スクリプトを共通アクセスの利用側にする
- `whereami.py` の参照先不整合を解消

### Phase 3: Codex用アダプターを追加

- Codexの公式な接続面を確認
- 最小のアダプターを一つだけ採用
- Codexが状態を読み取れることを確認
- ClaudeとCodexが同じJSONから同じ対象を解釈することを比較

### Phase 4: 実利用から再評価

- 同時セッション競合の有無を観測
- 必要な場合のみsession-local状態を導入
- 不要な製品固有フィールドが共通状態へ混入していないか確認

## 成功条件

次を満たしたとき、共有は成功したと判断できる。

- Claude CodeとCodexが同じ `environment_name` を認識する
- 両者が同じ `current_repo` を同じ意味で認識する
- home PCの状態がoffice PCへ混入しない
- 製品固有設定を `.home-ide-developer` に保存しない
- 一方のAI製品を削除しても共通状態の意味が変わらない
- 人間も同じ共通コマンドから状態を確認できる
- repository名またはローカル配置が変わっても一か所の修正で追従できる

## 未決事項

- `current_repo` を人間だけが更新するか、AIにも更新を許可するか
- Codexのどの接続面を利用するか
- 状態アクセスコマンドの正式名称と入出力形式
- schema versionが現時点で必要か
- session-local状態を導入する条件
- `current_repo` という名前を製品非依存の概念名として維持するか

## 結論

`.home-ide-developer` はClaude CodeとCodexの共通環境にできる。

ただし、共通化するのは両製品の設定ではない。人間、Claude Code、Codexが共有する、製品非依存のmachine-local環境状態である。

共通状態を中心に置き、Claude CodeとCodexを薄いアダプターとして接続する。この依存方向であれば、一方の製品仕様が変わってもホームIDE全体の意味を維持できる。
