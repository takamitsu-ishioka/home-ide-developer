# プロンプトとメモリー
- CLAUDE.md の適当な場所に以下を挿入
  - bin 直下にあまり多数置かない
  - bin の混雑回避のため bin/<同系ツールサブディレクトリ>を作成
  - 作成したら、~/.bashrc でパスを通す
  - export PATH が多くなり過ぎたら別ファイルに逃がす
  - 👇これを一般化して CLAUDE.md に記載
    claude_current_repo_announce.sh stdin (ダミーの必須引数)
    無引数で実行すると説明を表示
- agent が参照・更新する「メモリー」を哲学的に整理
  - 憲法、実定法、訴訟法、判例集
  - 憲法、実定法
    - 例： CLAUDE.md
    - 原則としてユーザーが管理する
  - 訴訟法
    - 例： agent が（半）自動的に記憶するもの
  - 判例集
    - 例：セッション・ログ
  以上をそれぞれダンプ(リポジトリ内のファイルに変換)する機能が必要。

# home-ide-developer
- claude と codex による共有
- docs の下に codex による設計あり

# SYNC
  ## 前提
  https://github.com/dominosoft-org/integrated-work-environment (Office dominosoft-org private)
  と
  git@github.com:takamitsu-ishioka/home-ide-developer.git (Home takamitsu-ishioka public)
  は
  - 目的は同じ、linux CLI による統合開発環境の開発
  - 対象と環境と制約は別
  - 共通の部品(スクリプトが結構ある)

  ## やりたいこと
  1. sync office to home
  2. sync home to office (Office 側で作業しないと、こっちは多分無理)

  ## 問題点
  単純なコピーはできない（ものが多い）

# ghost
- 権限問題: ghost-initialize で「参照専用ユーザー」を登録。で、解決する？

# misc
- codex のトークン資源消費量を表示するスクリプト

# 概念の整理
- client vs server
  - 軸: 依存関係
  - client: 目的を持つ者 = 手段を利用する者
  - server: 手段を持つ者 = 目的から利用される者
  - 原理: 手段は目的に依存する (「クリーンアーキテクチャ」の中核概念)
- inbound vs outbound
  - 軸: 情報移転の向き
  - inbound: 外から内へ
  - outbound: 内から外へ
- pull vs push
  - 軸: 通信のイニシエーター
  - pull: 情報を求める側がイニシエート
  - push: 情報を与える側がイニシエート
- internal vs external
  - 軸: 視点
  - internal: 系の内側から見る
  - external: 系の外側から見る
