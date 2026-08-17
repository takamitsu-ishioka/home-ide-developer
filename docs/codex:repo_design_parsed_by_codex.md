# Codexが実装から読み取ったリポジトリ設計

## この文書の位置づけ

この文書は、Codexが `home-ide-developer` のディレクトリ構造、設定、スクリプト、READMEを読み、そこから設計意図を復元した結果である。

このリポジトリでは実装がSSoTであり、本書は実装から導出された二次情報である。実装と本書が矛盾した場合は実装を優先する。

明示的に実装または既存文書で確認できた事項を「確認済み」、Codexによる解釈を「推測」として区別する。

## 一文で表した設計

> ホームディレクトリは、IDEである。

`home-ide-developer` はdotfiles集ではなく、Linuxユーザーのホームディレクトリ全体を、継続的に成長する開発環境として扱うためのリポジトリである。

## 物理構造

確認済みの概念構造は次のとおりである。

```text
~/                              home-ide-developerのclone先
├── .git/                       開発環境全体のGit履歴
├── .bashrc / .profile          シェル環境とPATH
├── .gitconfig / .gitignore     Gitの共通設定と追跡境界
├── bin/                        再実行可能な知識と操作
├── .claude/                    Claude Code固有の設定と指示
├── .codex/                     Codex固有の設定・状態・キャッシュ
├── .home-ide-developer/        このcloneに固有のmachine-local状態
├── <independent-repository>/   独立したGitリポジトリ
└── <submodule>/                必要に応じて参照するsubmodule
```

ホームディレクトリ直下に独立したGitリポジトリが存在し得る。このため、物理的には一つのディレクトリツリーだが、論理的には複数のリポジトリとツールから構成される。

既存規約にある表現を使えば、これは「物理モノリス・論理マイクロ」である。

## 複数PCにおける環境の単位

home PCとoffice PCは、それぞれ独立したファイルシステムと `~/` を持つ。両者を一つの巨大な共有ファイルツリーとして扱う設計ではない。

推測される配置モデルは次のとおりである。

```text
GitHub上のhome-ide-developer
        |
        +-- clone --> home PCの~/
        |              +-- home PC固有の状態とrepository
        |
        +-- clone --> office PCの~/
                       +-- office PC固有の状態とrepository
```

Gitで共有するのは環境の設計、共通設定、ツール、説明である。認証情報、キャッシュ、履歴、各PCの作業対象などはmachine-local状態として分離する。

したがって、あるPCの `/mnt/c/Projects/...` に存在するrepositoryやworktreeが、別のPCからも見えるとは限らない。

## `~/bin` の責務

`~/bin` は単なる便利スクリプト置き場ではない。人間またはAIが一度行った判断を、再実行可能なコマンドへ変換して蓄積する場所である。

```text
探索・推論
    |
    v
有効な操作を発見
    |
    v
bash/Pythonの小さなコマンドへ変換
    |
    v
人間とAIが同じコマンドを再利用
```

これはREADMEで「思考のコンパイル」「第二の脳」と説明されている。

設計上、AIは毎回すべてを推論する主体であるだけでなく、安定して再利用できる部品のメーカーでもある。推論の揺らぎをコマンドへ閉じ込め、以後の認知コストを削減することが目的である。

## 境界に対する考え方

設計原則は「バグは段差に湧く」である。

代表的な段差には次がある。

- WindowsとWSL
- GUIとCLI
- 人間とAI
- AIの推論と決定的なスクリプト
- GitHub上のrepository名とローカルディレクトリ名
- 環境共通状態とmachine-local状態
- 親repositoryと独立repositoryまたはsubmodule

なくせない段差は減らし、減らせない段差は一か所に集約する。`open_worktree.sh`、`vscode.sh`、`repo_name_sync.sh` などは、この原則を実装した境界アダプターと解釈できる。

## SSoTとGit追跡境界

確認済みの方針は次のとおりである。

Gitで追跡するもの:

- コード
- 共有設定
- ツール
- 一次文書
- 再現に必要なテンプレート

Gitで追跡しないもの:

- 認証情報と秘密鍵
- 実体の `.env`
- キャッシュ
- ログと履歴
- 再生成可能な二次情報
- machine-local状態
- 巨大ファイル

目的は、repositoryをcloneした人間またはAIが、同じシステムを理解し、再現し、変更できる状態を作ることである。

## `.home-ide-developer` の責務

`.home-ide-developer` は、ルート・ローカル・リポジトリ専用のデータ置き場である。

現在確認できる主な要素は次のとおりである。

| 要素 | 責務 | Git追跡 |
|---|---|---|
| `.repo-name-marker` | ディレクトリ名が変わっても場所を発見するための印 | する |
| `README.md` | ディレクトリの契約 | する |
| `environment_name.template` | 環境名ファイルのテンプレート | する |
| `environment_name` | このPCの環境名 | しない |
| `current_repo` | 現在注目するrepository | しない |

このディレクトリの名前は、GitHub上のrepository名をローカルへキャッシュしたものである。`repo_local_dir.sh` は名前をハードコードせず、`.repo-name-marker` から現在位置を解決する。

## 「現在位置」の複数の意味

この環境には、少なくとも次の異なる現在位置が存在する。

| 種類 | 例 | 意味 |
|---|---|---|
| 環境 | LOCAL | どの実行環境か |
| ホスト | PC名 | どの物理・仮想マシンか |
| cwd | `~/` | シェルが現在いる場所 |
| Git repository | home-ide-developer | cwdが属するrepository |
| branch/worktree | mainまたはfeature branch | Git上の作業単位 |
| current repository | `current_repo` の内容 | ユーザーが現在注目する対象 |
| agent session | Codex/Claudeのセッション名 | AIとの個別作業単位 |

これらは一致することもあるが、同一概念ではない。

たとえば、Codexを `~/` から起動しながら、別のworktreeを操作することができる。Codex画面に表示されるセッション名も、`current_repo` やGit branchとは別の識別子である。

## AIエージェントの位置づけ

Claude CodeとCodexは「IDEの中に追加された孤立機能」ではなく、シェル、Git、Pythonなどと同じく、ホームIDEを構成する道具である。

推測される理想的な依存方向は次のとおりである。

```text
人間 ─┐
      ├──> 共通コマンド ──> repository・外部サービス
Claude┤
Codex ┘
```

各AIが外部APIや複雑な操作方法を個別に再発明するのではなく、`~/bin` にある共通コマンドを利用する。新しく安定した操作を発見した場合は、再利用できるコマンドとして環境へ還元する。

## 現在確認できる不整合

`environment_name` の実体は `.home-ide-developer/environment_name` に置かれている。一方、`whereami.py` は現時点で `~/environment_name` を読む実装とコメントを持つ。

これは、状態の配置変更に利用側が追従していない内容不整合である。

また、`current_repo` は中立的なJSONデータだが、周辺スクリプトのコメントと利用経路はClaude Codeを前提としている。Codexとの共有はまだ実装されていない。

本節は不整合を記録するだけであり、この文書作成時点では修正していない。

## Codexによる総括

このrepositoryが作ろうとしているものは、特定のエディタ製品ではない。

シェル、Git、スクリプト、文書、AI、複数のrepositoryを、Linuxのホームディレクトリを中心に接続した、利用者固有の開発オペレーティング環境である。

その価値は、ツールの数ではなく、作業から得た知識がファイルとコマンドとして残り、次の人間とAIがそこから開始できる点にある。
