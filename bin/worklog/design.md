# worklog 設計書

## 目的（2026-08-25 再定義）

「作業報告」という行為そのものを無くすこと。人間が「今からticket Xの作業をします」と意識的に宣言してから作業する、という運用を前提にしない。

`integrated-work-environment`への一本化（常に`~/developer`単一リポジトリで作業する運用）により、職務上のほとんどすべての作業内容が既にClaude Codeセッションログに記録されている。これを事後的に解析し、

- ある時点でユーザーが行っていた作業の内容
- GitHub issue
- Jiraチケット

の対応関係を特定し、[Jiraダッシュボード10011](https://dominosvr.atlassian.net/jira/dashboards/10011)に表示される日次作業時間記録を、人間の目視確認・修正だけで作成できるようにする。

出典：`tmp/work.md`（2026-08-14時点の記述）。目的そのものを2026-08-25に再定義（下記アーキテクチャ参照）。

## アーキテクチャ：SSoT・交換形式・パイプライン（決定、2026-08-25）

- **SSoT（Single Source of Truth）**: Claude Codeセッションログ生データ（`~/.claude/projects/**/*.jsonl`）。人間もAIも書き換えない、既に存在する一次情報。
- **交換形式**: JSON配列。`worklog_session_turns_list.sh`が生成する、ターン（1プロンプト:1レスポンス）単位のレコード（`turn, timestamp, cwd, repo, ticket, user[], agent[]`。スキーマは§11）。
- **tsvは原則廃止**。人間による目視確認・編集は、VSCodeのJSONエディタ+検索で十分実用に足ると確認済み（`worklog_session_turns_list.sh`の出力を`json_pretty_print.sh`で整形し、1日分・数百行規模のJSONを問題なく編集できた）。
- **パイプライン**:
  ```
  SSoT(セッションログ) => 交換形式(JSON) => ヒト+lint.sh => 交換形式(検証済み) => 関連ツール
  ```
  「ヒト+lint.sh」は、人間がJSONを直接編集（ticket再割当・区間分割・note修正等）した後、機械的な妥当性検査（lintツール）を通す工程を指す（lintツール自体は未実装、下記「未決事項」参照）。

### freeeとの関係（決定、2026-08-25）

打刻データ（freee）は**「作業時間の外枠」として使わない**。実際には「休んでいたらTeamsで呼び出されて別作業が始まる」といったことが珍しくなく、打刻は実態を正確には反映しない、いわば「もっともらしいフィクション」に過ぎない。したがって：

- 交換形式の生成・ticket別セグメント化（§10・§11）はfreeeに依存しない。1日の外枠は、その日にセッションログへ実際に記録された最初のターン〜最後のターンそのものになる
- 将来的には逆に、交換形式（実際に何をしていたか）から**「もっともらしい打刻」を生成する**方向（freeeを交換形式から作られる二次データにする）を検討する。ただしこれは決定論的に機械化できる話ではなく、AIの力を要する。本worklogシステムの他の部分が完成してから、別途検討する（未決事項）

## 設計方針

CLAUDE.mdの方針に従い、AIの推論（揺らぐ・遅い・課金がかかる）に頼る範囲を最小化し、できるだけ多くの処理を決定論的なスクリプトで実行する（[[feedback_ai_as_parts_maker]]）。AIの判断が必要な箇所（作業内容とissue/チケットの対応特定など）は、AIが候補を提示し、最終確定は必ず人間が行う。

## 全体設計

### 1. セッション開始時の作業コンテキスト宣言（決定）

（注：実体は`bin/claude/claude_launch.sh`。§9で`cwd_chain_show.sh`による起動時のstderr表示を実装済みだが、それは人間向けの表示に過ぎず、下記の「claudeへの最初の発言として渡す」仕組みそのものはまだ未実装）

`claude_session_launch.sh`の起動引数に、素の引数（`-p`は付けない）として作業コンテキストを渡す。

```bash
claude_session_launch.sh "{repo: integrated-work-environment, issue: none}"
```

`-p`/`--print`は非対話・一発応答モードのため使わない。素の引数は対話セッションの最初の発言として渡り、以降も対話が継続する。

### 2. セッション中の「次は？」フロー（決定）

ユーザーが「次は何でしょう？」と尋ねると、AIがそのセッションを遡り、未確定・未決の作業候補を`{repo, issue, note}`の形で最大`MAX_TODO_COUNT`件（`~/bin/worklog/config.json`で設定）提示する。ユーザーは番号を指定して確定する。

```
user: 次は何でしょう？
claude:
  1.
    repo: foobar
    issue: bug/123 "..."
    note: ...
  2.
    repo: none (defaults to integrated-work-environment)
    issue: none
    note: ...
user: 1 で。
```

ユーザーが番号で確定した時点、または「今日はここまで」のように終業を宣言した時点で、**Claudeが`worklog_entry_start.sh` / `worklog_entry_end.sh`（§7参照）を呼び出す**。ユーザーが自分でシェルからこれらを叩く運用は想定しておらず、あくまで自然言語のやり取りがトリガーになる（[[feedback_ai_as_parts_maker]]：AIがAPIやファイル操作を直接行うのではなく、スクリプト化されたものを呼ぶ）。ただしスクリプト自体はどちらが呼んでも同じ動作をするため、手動実行を妨げるものではない。

**引数の可視性（決定）**：Claudeがこれらを自動で呼ぶ際は、実行直前に「どのコマンドをどんな引数で呼ぶか」を対話画面上のテキストとして必ず一言明示してから呼び出す。スクリプト自身も書き込み前に`入力:`ブロックをstderrへ出す設計（§7）だが、それに加えてClaude側の発話でも明示することで、ツール呼び出しの表示がUI上で省略・折りたたまれる場合でも、ユーザーが常に「何が実行されようとしているか」を対話画面のテキストだけから確認できるようにする。

候補生成の具体的な手がかり（担当中Jiraチケット一覧／開いているPR一覧／セッション内容など）は未確定（下記「未決事項」参照）。

（注：本フローと`worklog_entry_start/end.sh`の打刻方式は、§目的で再定義した「作業報告という行為を無くす」という方針とは別系統として残っている。位置づけの見直しは「未決事項」参照）

### 3. 保存場所・命名（決定）

`~/bin/worklog/` に実行ファイル・設定・蓄積データをまとめて置く。

- `~/bin/freee/`に既に`time_clock_punch.log`（非実行ファイル、git管理下）が同居している前例があり、実行ファイルとデータの混在はこのリポジトリの既存の流儀と一致する。
- `~/bin`を単一の起点とする「ツール体系」の思想（CLAUDE.md）にも、`~/bin`配下に置く方が合致する。
- 名前を`worklog`とした理由：最終的な出力先であるJira自身が「Log work」「Worklog」という用語をネイティブ機能名として使っており、「ローカルのworklog → Jiraのworklog」という対応が名前だけで分かるようにするため。`work_time`は既存の`freee/`（勤怠・勤務時間）と語感が被り紛らわしいため避けた。

### 4. Jiraダッシュボード10011の実体調査（決定・完了・実測で更新）

このダッシュボードが何のデータから作られているかを特定した。書き込み先のAPIはこれで決まる。

#### 調査結果（表示側）

ダッシュボード10011（タイトル「作業時間」）内の**「Timesheet」ガジェット**の下部に「Provided by Time Tracker · Contact support」の表記を確認した。これはMarketplaceアプリ名を明示する定型表記であり、ガジェット追加パネルに表示される「Time Tracker（作成者: Tempo Software）」と一致する。

→ **表示（Timesheetガジェット）はTempo社の「Time Tracker」アプリ（Tempo Timesheets）製と確定**。

なお、ダッシュボードには「Working time check (powered by freee API)」という行もあり、合計時間と一致していた。既存の勤怠システムfreee（`bin/freee/`参照）とTempoのログ時間を突き合わせる社内カスタム連携が既に存在する可能性がある。

#### 実測結果（書き込み側・2026-08-20）

当初は「表示がTempo製 → 書き込みもTempo専用API必須」と推測したが、これは誤りだった。ドミノポータル（`dominosoft-org/domino-portal`、`backend/routes/jira.ts`）が**Jiraネイティブworklog API**（`/rest/api/2/issue/{issueKey}/worklog`、Basic認証＝各ユーザー個人のメールアドレス＋Jira APIトークン）だけで作業時間登録を実現していることをソースで確認し、同じ方式で検証スクリプト`worklog_jira_post.sh`を作成。GENERAL-451に対し実際にPOSTしたところ、**ダッシュボード10011のTimesheetガジェットに即座に反映された**（実測で確認。CLAUDE.mdのDJC原則「昨日の演繹より今日の帰納」の実践）。

→ **書き込み先はJiraネイティブworklog API（`/rest/api/2/issue/{id}/worklog`）で確定。Tempo側API（`api.tempo.io`）・Tempo専用トークンは不要**。表示はTempo製アプリだが、内部でJiraネイティブworklogを取り込む設定になっている模様（Tempo Account/Team等のTempo固有フィールドを使わない限りは、という留保付き）。

これにより、下記「未決事項」にあった「Jira管理者権限待ち」のブロッカーは解消。各ユーザーが自分のJira APIトークンを個別発行するだけで実装を進められる。

#### 調査方法（参考：実施した手順）

1. 各ガジェットの右上メニュー→「ガジェットを編集」で参照しているJQL/レポートタイプを確認
2. ガジェット名・UIに「Tempo」の表記があれば、Tempoアプリ使用の可能性が高い
3. ガジェット下部の「Provided by」表記でMarketplaceアプリ名を直接確認
4. ブラウザ開発者ツールのNetworkタブでAPIリクエストを観察する方法（`/rest/tempo-timesheets/...`や`api.tempo.io/...`）もあるが、今回は不要
5. チケットの「Log work」ダイアログの見た目（Jira標準かTempo独自UIか）でも判別可能
6. 権限があればJira管理画面 → Apps → Manage appsで導入済みアプリ一覧を確認
7. **表示側の調査（1〜6）だけで書き込み側APIを断定しない。実際にJiraネイティブAPIでworklogを1件POSTし、ダッシュボードに反映されるか実測するのが最も確実**（今回はこれで最終確定した）

### 5. セッションの日次分割（今回設計・実装対象）

#### 課題

`claude_session_launch.sh`は常に`--resume`でセッションピッカーを開く設計だった。ピッカーでの選択はユーザーの手作業判断に委ねられ、日をまたいでも同じセッションを選び続けてしまうと、セッションが際限なく肥大化する。また「次は？」フローで「その日のセッションを遡る」ためには、そもそも1日1セッションに区切られている必要がある。ピッカー任せは決定論的でなく、CLAUDE.mdの方針（できるだけ多くの処理を決定論的に実行する）にも反する。

#### 設計

1. 起動時、現在の`pwd`と一致する`cwd`を持つセッションのうち、最終更新時刻（mtime）が「今日」（ローカル日付）であるものを`~/.claude/projects/`配下から探す。
   - `~/.claude/projects/<encoded-path>/`のディレクトリ名エンコード規則（`/`→`-`等）は非公式かつ不確実なため信頼せず、各`.jsonl`内の各行に実測で存在が確認できた`cwd`フィールドと文字列一致で照合する方式を採る。
   - `subagents/`配下は除外する（`claude_session_to_markdown.py`・`claude_session_log_clean_up.py`と同じ扱い。フォークされたサブエージェントの会話であり、「今日の本セッション」ではないため）。
2. 該当が1件 → そのセッションIDを直接指定し`--resume <id>`で再開する（ピッカーを経由しない、完全に決定論的）。
3. 該当が0件 → `--resume`を付けず新規セッションとして起動する（新しいセッションIDが自動生成される）。
4. 該当が複数件 → mtime最新の1件を選び、残りはstderrに一覧表示するだけに留める（決定論的なtie-break。人間の判断は挟まない）。

#### 実装物（予定）

- `bin/claude_session_today_find.sh` / `.py`：cwdを引数に「今日」のセッションIDを検索する部品。`claude_session_launch.sh`だけでなく、将来「次は？」フロー（その日のセッションを遡る処理）でも再利用する想定。
- `bin/claude_session_launch.sh`の改修：上記を呼び出し、`--resume <id>`か新規起動かを分岐する。

### 6. worklog登録の実API呼び出し（決定・実装済み）

`worklog_jira_post.sh` / `.py`：`<issue_key> <started> <time_spent_seconds> <comment>`を引数に、Jiraネイティブworklog API（`/rest/api/2/issue/{issueKey}/worklog`）へBasic認証（`JIRA_EMAIL` + `JIRA_API_TOKEN`、`~/bin/worklog/.env`）でPOSTする。`--dry-run`（送信内容のみ表示）・`--confirm`（送信前にY/n確認）に対応。2026-08-20、GENERAL-451への実POSTでダッシュボード10011への反映を確認済み（§4参照）。

### 7. 確定した作業の保存フォーマット（廃止済み、2026-08-25）

「作業報告という行為を無くす」という目的（本ドキュメント冒頭）と、都度の宣言を前提とするこの方式は原理的に矛盾するため、§10「新方式」導入と同時に`worklog_entry_start.sh`/`worklog_entry_end.sh`・`worklog_tsv.py`・`worklog.tsv`を削除した。以下は過去の設計（参考のため残す）。

#### 設計（旧）

既存の`~/bin/worklog/worklog.tsv`（`date, start, end, duration, repo, issue, note, posted_at`のTSV、git管理下）をそのまま蓄積先とする。新規ファイルは作らない。

記録方式は`bin/freee/time_clock_punch.sh`の打刻（clock_in/clock_out）と同じ「パンチ方式」を採る。ユーザーが番号で確定した瞬間に分かるのは`{repo, issue, note, timestamp(=今この瞬間)}`だけであり、その作業がいつ終わるかはまだ分からない。したがって：

1. 確定時（`worklog_entry_start.sh <repo> <issue> <note>`）：もし直前に`end`未確定（空欄）の行があれば、その`end`を現在時刻で埋めて閉じたうえで、新しい行を`start=現在時刻, end=空欄`で追加する（＝新しい作業の開始は、直前の作業の終了を意味する）。
2. 終業宣言時（`worklog_entry_end.sh`）：直前の`end`未確定の行があれば、その`end`を現在時刻で埋めて閉じる。新しい行は追加しない。今回の会話中の「今日はここまでとします」がまさにこの操作のトリガーの実例。

これにより、ユーザーは`start`と`end`を意識して入力する必要がなく、「次はこれ」「今日はここまで」という自然な発話のタイミングだけで、`worklog.tsv`が自動的に一貫した状態（重複や隙間のない区間の列）に保たれる。

#### 日またぎガード（決定）

ユーザーが何も言わずにセッションを抜けると、`worklog_entry_start.sh`/`worklog_entry_end.sh`のどちらも呼ばれないまま未確定行が残り続ける。この状態で後日改めて`worklog_entry_start.sh`（または`worklog_entry_end.sh`）が呼ばれると、素朴には「現在時刻で閉じる」処理が走り、実態と無関係な所要時間（日をまたいだ長時間）が`worklog.tsv`に混入してしまう。

これを防ぐため、直前の未確定行の`date`が今日と異なる場合は、**自動では閉じずにエラー終了し、ユーザーに手動修正を促す**（新規行も追加しない）。「何時間以上を異常とみなすか」といった閾値は設けない。既存の`date`列という事実だけで判定できる「日をまたいでいるか」だけを基準にする（推測でendを埋めない、CLAUDE.mdの「推測で補完した場合は必ずその旨を明示する」に沿い、そもそも推測自体をしない設計）。

なお、Claude Codeには`SessionEnd`フック（セッション終了時に外部シェルコマンドを実行する仕組み）が存在するが、「ユーザーが何も言わずターミナルを閉じた」ような不本意な離脱でも確実に発火するかはドキュメント上確認できなかった。フックの信頼性に依存させると「発火しなかった場合」の壊れ方を作り込むことになるため、**このプロジェクトではSessionEndフックは使わない方針とし、上記の日またぎガードのみで対応する**。

#### 実装物（削除済み、2026-08-25）

- `bin/worklog/worklog_entry_start.sh` / `.py`：`<repo> <issue> <note>`を引数に、直前の未確定行を閉じてから新規行を追加。日またぎガードあり
- `bin/worklog/worklog_entry_end.sh` / `.py`：引数なし。直前の未確定行を閉じるのみ。日またぎガードあり
- `bin/worklog/worklog_tsv.py`：TSVの読み書きと、日またぎガード判定(`is_stale`)を両スクリプトで共有する部品
- 両方とも`--dry-run`（変更内容の表示のみ）に対応。TSVへの追記・書き換えという副作用があるため、実行前に変更内容を一箇所で明示する（CLAUDE.mdの規約）

### 8. mmwaveチームにおける cwd => issue の解決（決定・実装済み）

「候補生成ロジック」（未決事項）のうち、ミリ波チームの開発（`fl-mmwave`）に限定した`cwd => issue`の解決方法が決まった。

#### 調査結果

- `dominosoft-org/mmwave_tools`は`integrated-work-environment`の前身にあたり、今後は使わない
- ミリ波チームの実際の開発は`uenoyama-dominosoft/fl-mmwave`（別GitHub組織、`dominosoft-org`ではない）で行われ、`/mnt/c/Projects/mmwave/fl-mmwave`にローカルclone、`/mnt/c/Projects/mmwave/worktrees/`配下にissueごとのgit worktreeを作る運用
- Jiraチケット側の`description`本文に、ADFの見出し「### GitHub Issue」＋直後の段落にissue URLという形で、GitHub issueへの参照が埋め込まれている（Remote Link・カスタムフィールドではない）。MMWAVE-875で実測確認済み
- worktreeのディレクトリ名・ブランチ名の命名は従来ブレていた（`feature/#221-...`、`feature-448-...`など不統一）

#### 決定した規則

worktreeディレクトリ名は常に`<issue_number>-<slug>`（接頭辞語`feature-`/`bug-`は廃止）。ブランチ名はチーム全体の慣習に関わるため本設計では固定せず、スクリプト引数として明示的に渡す。「issueなくして開発なし」を例外なく適用し、issueの無いworktreeは許容しない（issue作成を促す）。既存の非準拠worktreeはリネームしない（今後の新規作成分にのみ適用）。

#### 実装物

- `bin/mmwave/worktree_create.sh <issue_number> <slug> <branch>` / `.py`：`gh issue view`でissueの実在を検証してから`git worktree add`する。`issue_number`が必須引数のため、issueを持たずに呼び出す形自体が作れない。ブランチが既存なら流用、無ければ`origin/develop`から新規作成。`--dry-run`/`--confirm`対応
- `bin/mmwave/development_environment_lint.sh` / `.py`：読み取り専用。`/mnt/c/Projects/mmwave/worktrees/`配下の全worktree名を`^\d+-[a-z0-9-]+$`で検査する。§9のcacheと合わせ、`cwd => repo => issue => ticket`の連鎖全体を一望できるよう拡張済み（`ok`/`wrong_format`/`no_issue`/`no_ticket`をTSVで報告、`ticket_key`列も出力）。違反があれば非0終了

### 9. issue => ticket の順方向解決と cwd => issue => ticket の高速合成（決定・実装済み）

#### 調査結果（想定の訂正）

§8では`MMWAVE-875`1件のみの実測に基づき、「### GitHub Issue」見出し＋直後の段落のリンク、という形式を想定していた。しかし`project = MMWAVE AND updated >= -90d`（116件）を実測した結果、この形式に従うのは1件のみで、残りの大半（116件中91件で抽出成功）は別形式（見出しテキストは「作業内容」など不統一、リンクはADFの`inlineCard`ノードの`attrs.url`）だった。加えて、参照先GitHubリポジトリは`fl-mmwave`だけでなく`mmwave_sensor_issues`・`mmwave_server_issues`など複数存在することも判明した。ごく少数（実測2件）のチケットには複数のGitHub issueリンクが埋め込まれており、この場合はdoc内出現順で先頭を採用しstderrに警告する（推測で1件に絞ったことを明示、CLAUDE.mdの方針に沿う）。

この教訓により、抽出ロジックは「特定の見出し位置」に依存せず、description全体を走査してGitHub issue URL（`inlineCard`/`blockCard`のurl、テキストのlinkマーク、平文いずれも）を拾う方式に変更した。1サンプルだけで確定した仕様を後から実データで覆した実例（DJC的には「1件の演繹」より「複数件の帰納」を優先した形）。

#### 決定した設計

- issue => ticketの対応は、都度JQL検索で全文を舐めるのではなく、事前にローカルcacheに蓄積し、高速に引けるようにする
- cacheの保存場所は`~/.integrated-work-environment/issue_ticket_cache.json`（`bin/worklog`固有のデータではなく、`bin/worklog`・`bin/mmwave`など複数ツールが横断的に参照する共有stateのため、特定ツールのディレクトリ配下ではなくホーム直下の専用ディレクトリに置く。Jira等から再生成可能な二次情報のため`.gitignore`で除外）
- 形式はJSON（`repo => issue_number => {ticket_key, synced_at}`という入れ子構造）。1つのrepoに対しissueは一対多であり、TSVの行の羅列よりもJSONの入れ子構造の方が素直に表現できるため（CLAUDE.mdの「複雑な構造の場合はJSON」の指針にも合致）
- cache更新はJQLで対象を絞って明示的に実行する`issue_ticket_sync.sh '<jql>'`。マージ方式（既存cacheの他エントリは温存し、今回ヒットした分だけ上書き）で冪等
- cwd => issueは、`<issue_number>-<slug>`という既存のworktree命名規則（§8）をそのまま利用し、`git remote get-url origin`からrepo名、ディレクトリ名先頭の数字からissue番号を取り出す
- 上記2つを合成した`cwd_to_ticket.sh`で、cwdを渡すだけで一気にticket_keyを引ける
- `bin/mmwave/development_environment_lint.sh`（§8）を拡張し、fl-mmwave配下の全worktreeについて`cwd => repo => issue => ticket`の連鎖全体を一望できるようにした（`no_ticket`ステータスを追加）

#### 実装物

- 配置の訂正（2026-08-21）：以下4本は当初`bin/worklog/`に作ったが、worklog専属ではなく`cwd => repo => issue => ticket`連鎖の解決ロジックそのもの（mmwaveのlint、claude_launchのstatusLine表示からも参照される）と判明したため、`bin/integrated_work_environment/`へ移動した。Jira認証情報（`.env`）は唯一の保管場所である`bin/worklog/.env`を引き続き共用する。`bin/worklog/`には`worklog.tsv`本体を操作する`worklog_entry_start/end.sh`・`worklog_jira_post.sh`・`worklog_jira_issue_get.sh`・`worklog_tsv.py`のみが残る
- `bin/integrated_work_environment/repo_issue_from_cwd.sh <cwd>` / `.py`：cwd（gitワークツリー）からrepo名とissue番号をTSVで返す。読み取り専用
- `bin/integrated_work_environment/issue_ticket_sync.sh <jql> [--dry-run] [--confirm]` / `.py`：JQLでヒットしたチケットのdescriptionからGitHub issue URLを抽出し、`~/.integrated-work-environment/issue_ticket_cache.json`をマージ更新する。手動でcacheを更新する唯一の手段。descriptionはあるがGitHub issueリンクが見つからないチケットは、issue作成＋リンクを促すため一覧（`{JIRA_BASE_URL}/browse/{key}`）をstderrに表示する（description皆無のチケットは対象外＝開発と無関係と判断）
- `bin/integrated_work_environment/ticket_from_issue.sh <repo> <issue_number>` / `.py`：cacheを引いてticket_keyを返す。読み取り専用
- `bin/integrated_work_environment/cwd_to_ticket.sh <cwd>`：上記2つをbashで合成するだけの薄いスクリプト（合成処理自体は単純なため、python部品は作らず直接bashで書く）
- `bin/mmwave/development_environment_lint.sh`（§8参照）を拡張し、`ok`な各worktreeについて上記cacheを引いて`ticket_key`列を追加、見つからない場合は`no_ticket`ステータスで報告するようにした
- `bin/integrated_work_environment/cwd_chain_show.sh <cwd>`：1件のcwdについて`cwd => repo => issue => ticket`を1行で表示する。読み取り専用、途中で解決できなくても（野良セッション・ticket未同期）エラー終了せず分かる範囲を表示する。`bin/mmwave`・`bin/worklog`どちらの専属でもない横断的ツールのため、`bin`直下の混雑回避方針（`.bashrc`のコメント参照）の延長として新設した`bin/integrated_work_environment/`に置く
- `bin/claude/claude_launch.sh`に統合済み：`session_name`確定直後・`exec claude`の前に`cwd_chain_show.sh "$(pwd)"`をstderrへ出力し、どのモード（`today`/`resume`/`new`/直接指定/`--`スルーパス）で起動しても必ず一度、起動時に連鎖状態が地味に表示される
- 実測: `project = MMWAVE AND updated >= -90d`で116件中91件からGitHub issueリンクを抽出、`fl-mmwave`/`mmwave_sensor_issues`/`mmwave_server_issues`の3リポジトリが混在することを確認。`development_environment_lint.sh`実行で全7worktreeの連鎖状態を一望でき、3件が`ok`（`ticket_key`取得済み）、1件が`no_ticket`（issueはあるがticket未同期）、2件が`wrong_format`、1件が`no_issue`と判定されることを確認済み。`cwd_chain_show.sh`も解決成功／ticket未同期／野良セッション（gitリポジトリ外・worktree命名規則外）の3パターンで実測確認済み

### 10. セッションログからのticket別作業時間推測・一括登録

#### 旧方式（2026-08-24、アーカイブ）

以下は2026-08-25、下記「新方式」（交換形式JSON経由）へ置き換えられた過去の設計。参考のため残す。

##### 課題

打刻方式（§7）は、ユーザーがticket切り替わりの都度「次はこれ」と宣言することが前提であり、宣言を忘れた日や、後から振り返って複数ticketにまたがる作業時間を一括整理したい場合に対応できない。一方でセッションログには実際の作業内容（cwdの変遷）が既に記録されている。

##### 検討の経緯

当初は「ターンごとの実働時間（`turn_duration`イベントの積算）」方式を検討したが、離席・アイドル時間の扱いに恣意的な閾値判断が必要になり複雑だった。ユーザー提案により、**freeeの打刻という信頼できる実測値を1日の外枠として固定し、その中を`ticket_id`の変わり目だけで単純に分割する**方式へ転換した。この方式ではアイドル時間の扱いという概念自体が発生しない（開始〜終了の合計は常にfreeeの実働時間と一致する）。

（2026-08-25追記：この後、freeeの打刻は実態を反映しない「もっともらしいフィクション」であり外枠として使うべきではない、という判断に転換した。下記「新方式」参照）

##### 決定した設計（旧）

1. 対象日のセッションログ全件から`type:"system", subtype:"turn_duration"`イベント（`timestamp`・`cwd`を直接持つ、Claude Code側で既に1ターン単位に計算済みの一次情報）を「ターン」として抽出する
2. 各ターンの`cwd`を`cwd => repo => issue => ticket`連鎖（§9）で解決し`ticket_id`とする。解決できない場合（野良セッション・ticket未同期）は`ticket_id = GENERAL-451`（その他の雑多な作業のdefault）とする
3. その日の全ターンをtimestamp昇順に並べ、freeeの打刻記録（`bin/freee/time_clock_get.sh`）から得た**最初の`clock_in`〜最後の`clock_out`**を全体の開始・終了とする
4. `ticket_id`が変わった地点、および休憩（`break_begin`/`break_end`）の開始・終了の地点でセグメントを区切る。休憩区間は`ticket_id = "(休憩)"`という専用の値になり、休憩終了後は休憩開始前の`ticket_id`に復帰する
5. 結果は`worklog.tsv`と同一スキーマの候補行としてTSVで出力する（副作用なし）。人間が目視チェック・編集した上で`worklog.tsv`へ追記し、`worklog_jira_post_batch.sh`で一括投入する

##### `worklog.tsv`のスキーマ拡張（実施済み、現在も有効）

`posted_at`列を追加（既存6列 → 7列）。空欄=未投稿。一括投稿後に書き込まれ、再実行時の二重登録を防ぐ。手動打刻（`worklog_entry_start.sh`）で追加される新規行も空文字で書き込む。

追記（2026-08-24）：`end`の右に`duration`列を追加（7列 → 8列、`date, start, end, duration, repo, issue, note, posted_at`の順）。`start`/`end`から常に導出可能な値で新情報ではないが、レビュー時に暗算せず一目で所要時間がわかるよう`worklog_tsv.duration_hm()`で計算して持たせる。`worklog_entry_start.sh`/`worklog_entry_end.sh`は行を閉じる（`end`を確定する）タイミングで併せて計算・書き込む。ついでに、`worklog_tsv.write_rows()`が`csv.DictWriter`のデフォルト`lineterminator`（`\r\n`）のままだったため`worklog.tsv`にCRLFが混入していたことに気づき、`lineterminator="\n"`を明示してリポジトリの他ファイルと改行コードを揃えた。

##### 実装物（旧、現在は`worklog_session_infer.py`は新方式に置き換わっている）

- `bin/freee/time_clock_get.sh <date>` / `.py`：freeeの指定日の`time_clocks`（打刻イベント一覧）を`type\tdatetime`のTSVで返す。読み取り専用（新方式では未使用）
- `bin/worklog/worklog_jira_api.py`：`worklog_jira_post.py`からJira worklog POSTの実処理（`post_worklog()`・`resolve_started()`）を切り出した共有部品。単発投稿・一括投稿の両方から使う（`JiraApiError`を送出し、exit方法は呼び出し元CLIが決める）
- `bin/worklog/worklog_jira_post_batch.sh [--dry-run] [--confirm]` / `.py`：`worklog.tsv`の未投稿行（`end`確定済みかつ`posted_at`空欄）をまとめてJiraへPOSTする。1行の失敗が他行の投稿を止めないよう、行ごとに結果を記録し、成功した行だけ`posted_at`を書き込む
- `bin/worklog/worklog_jira_post.py`：上記共有部品を使うようリファクタ（CLI仕様・出力は変更なし）
- 実測（2026-08-21分、旧方式）：85ターン・1回の休憩から6区間に分割。08:53〜16:35（freeeの実働時間と完全一致）のうち、`fl-mmwave`worktree（`MMWAVE-922`）でのターンが2区間、休憩が1区間、残りは`GENERAL-451`（`/home/developer`直下＝野良セッションでの作業）に分類された

##### 逆方向（Jira => worklog.tsv）の同期・整合性検査（実施済み、現在も有効）

`worklog_jira_post_batch.sh`（worklog.tsv => Jira）を実装・検証する過程で、Jiraダッシュボード10011を見たユーザーが「17日は既に記入済みかつ整合的に見える」と気づいた。調査の結果、`worklog.tsv`の未投稿行（MMWAVE-787、55分）と、Jira側に既に存在する実績（同じく55分）が完全一致していることが判明。これは恐らく過去に別経路（単発の`worklog_jira_post.sh`実行など）で既に投稿済みだったにもかかわらず`posted_at`が空欄のまま残っていた状態で、このまま一括投稿すると二重登録になるところだった。CLAUDE.mdのDJC原則そのもの（Jira側とworklog.tsv側という独立した2つの情報源を比較して不一致を検出）。

これを踏まえ、逆方向の同期ツールと、期間を指定した整合性検査ツールを追加した。

- `bin/freee/work_record_get.sh <date>` / `.py`：freeeの指定日の`work_record`（日次集計。`day_pattern`・`paid_holiday`・`is_absence`等の勤怠区分を含む）をJSONでそのまま返す。読み取り専用
- `bin/worklog/worklog_jira_query.py`：Jira worklog検索・取得の共有部品（`worklog_jira_sync.py`・`worklog_jira_validate.py`両方から使う）。JQL（`worklogAuthor = currentUser() AND worklogDate >= ... AND worklogDate <= ...`）で該当issueを検索し、各issueのworklog一覧を取得・期間と自分（`JIRA_EMAIL`）でフィルタする
- `bin/worklog/worklog_jira_sync.sh <date> [--dry-run] [--confirm]` / `.py`：指定日のJira worklog（自分の分）を`worklog.tsv`へ取り込む。issueごとに1対1でローカル未投稿行と対応付けられれば`posted_at`を埋め（二重登録防止）、対応するローカル行が無ければ新規行として追加する。1対1に対応付けられない場合は人間の確認に委ね、何も書き換えない
  - バグ修正（2026-08-24）：ローカル行の判定を「未投稿行のみ」で行っていたため、既に同期済み（投稿済み）のissueを「ローカルに無い」と誤認し、再実行のたびに重複行を追加してしまう不具合があった。判定対象を投稿済み行も含めた全ローカル行に変更し、全て投稿済みなら「既に反映済み」として何もしないようにした
- `bin/worklog/worklog_jira_validate.sh <from_date> <to_date>`（読み取り専用） / `.py`：期間を指定し、`worklog.tsv`とJira worklogの整合性を報告する。
  - ticketレベルの記録（local/Jiraどちらか）があるdate+ticketは1行1組で報告し、`status`列は常に`work`。記録が一件も無いdateはfreeeの`work_record`から`day_pattern`・`paid_holiday`等を見て、`ticket`〜`match`列を`-`にした専用の1行で日単位に分類する：`day_pattern`が`prescribed_holiday`/`legal_holiday`なら`holiday_public`、`paid_holiday`等が入っていれば`holiday_private`、`is_absence`なら`absence`、`clock_in_at`があるのに記録が無ければ`not_posted_yet`、それ以外は`unknown`
  - `local_state`（`posted`/`unposted`/`mixed`/`none`）と`match`（`match`/`mismatch`/`-`）の2軸に分解して報告する（「複数の軸が混じっている」との指摘を受けた設計）
  - 問題として扱う組み合わせ: `match=mismatch`（常に）／`local_state=mixed`（常に）／`local_state=posted`かつremoteに記録なし／`local_state=unposted`かつ`match=match`
  - stderrに問題行ごとの対処法（GUIDANCE）を表示。ttyならANSIカラー強調、非ttyなら`flag`列（`*`/`-`）
- 実測（2026-08-17〜23）：MMWAVE-787の二重投稿を検出、`worklog_jira_sync.sh 2026-08-17 --confirm`で解消。18日=`holiday_private`（有給）、22・23日=`holiday_public`（所定休日）、20・21日=`not_posted_yet`（後日記録して解消）を正しく分類することを確認済み

#### 新方式：交換形式(JSON)を経由したticket別時間集約（決定・実装済み、2026-08-25）

freeeの打刻を外枠として使わない方針転換（アーキテクチャ節参照）と、TSV原則廃止の方針を受けて、旧方式を置き換えた。

##### 決定した設計

1. `worklog_session_turns_list.sh <date> <limit>`（読み取り専用）が、対象日のセッションログ全件から交換形式（§11）のJSON配列を出力する（SSoT => 交換形式）
2. `worklog_session_infer.sh`（読み取り専用、freee非依存）が、上記JSONをstdinで受け取り、`(repo, ticket)`が連続する区間をまとめてticket別の作業時間候補をJSON配列で出力する
   - 1日の外枠は、旧方式のfreee clock_in/clock_outではなく、**その日のturns自体の最初〜最後のtimestamp**になる
   - 休憩の概念は無い（休憩情報の出所だったfreee打刻を使わないため）。ticketの変わり目だけがセグメント境界
   - `note`は、セグメント内の最初の非空`user`発言を初期値とする（`ticket == GENERAL-451`かつ発言が見つからない場合のみ「その他の雑多な作業」という定型文）。実際の会話内容がそのままnoteの下書きになる
3. 人間がJSONを直接編集（VSCode等）してticket再割当・区間分割・note修正を行い、`bin/worklog/log/<date>.json`として保存する
4. `worklog_lint.sh`で妥当性検査後、Jira投稿ツールへ渡す（§12参照）

```bash
worklog_session_turns_list.sh 2026-08-24 none | worklog_session_infer.sh
```

##### 実装物

- `bin/worklog/worklog_session_turns_list.sh <date> <limit>` / `.py`：交換形式の生成元。詳細は§11
- `bin/worklog/worklog_session_infer.sh` / `.py`：交換形式(stdin) => ticket別セグメント(JSON)への集約。旧版が自前で行っていたfreee参照・`cwd=>ticket`解決は、両方とも交換形式生成側（`worklog_session_turns_list.py`）へ移した結果、純粋なJSON変換ロジックのみになった（`repo_issue_from_cwd.sh`・`ticket_from_issue.sh`への依存も無くなった）
- 実測（2026-08-21再実行、旧方式との比較）：85ターンから5区間に分割（旧方式は6区間）。区間数の差は、(a)休憩分割が無くなったこと、(b)`cwd => ticket`解決が現在のマッピング状態を参照するため、08-21当時と結果が変わりうること（実際に`56-carecom`worktreeのticket解決が`MMWAVE-922`→`GENERAL-451`に変化していた）、の2点による。(b)は交換形式の生成ロジックそのものの性質（過去日の再解決は現在の設定次第で変わりうる）であり、今回の書き換えによる回帰ではない
- 実測（2026-08-24分）：78ターンから3区間に分割、noteに実際のユーザー発言が反映されることを確認。ただしnoteの初期値が`/compact`等のスラッシュコマンドのエコーになるケースがあり、これは未対応（次フェーズで改善の余地あり）

### 11. 交換形式（JSON）のスキーマ（決定・実装済み、2026-08-25）

`worklog_session_turns_list.sh <date> <limit>`が生成する。対象日のセッションログを「ターン」（`type:"system", subtype:"turn_duration"`イベントで区切られる、1プロンプト:1レスポンスの単位。Claude Code側で既に計算済みの一次情報）ごとに1レコードとして出力する。

| フィールド | 内容 |
|---|---|
| `turn` | turn_duration イベントのuuid（識別子。個々のturnを一意に指す） |
| `timestamp` | ターン完了時刻（ISO8601、Asia/Tokyo） |
| `duration_ms` | そのターン自身の処理時間(ms)。`turn_duration`イベントの`durationMs`をそのまま転記（決定・実装済み、2026-08-27）。`timestamp - duration_ms`がそのターンの処理開始時刻になる。regularizeステップでのgap検出に使う |
| `session_id` | `turn_duration`イベントの`sessionId`をそのまま転記（決定・実装済み、2026-08-27）。regularizeステップで「セッションを跨いだか」の判定に使う |
| `cwd` | ターン発生時の作業ディレクトリ |
| `repo` | `cwd => repo => issue => ticket`連鎖（§9）で解決したrepo表示名（解決できなければ`none`） |
| `ticket` | 同上、ticket_key（解決できなければ`GENERAL-451`） |
| `ticket_url` | `ticket`のJiraチケットURL（`{JIRA_BASE_URL}/browse/{ticket}`）。人間が目視確認する際にワンクリックで元チケットへ飛べるようにする（決定・実装済み、2026-08-27） |
| `user` | そのターンで人間が実際に打った発言の生テキストの配列。`<system-reminder>`等の注入テキストは除去。画像は含めない（画像から読み取れる文章は、既にテキストとして存在する限りそのまま含む） |
| `agent` | トップレベルagentのユーザー向け発言の配列（`thinking`ブロックや通常のtool_use/tool_resultは含めない）。サブエージェント（Agentツール）呼び出しは対話内容そのものを含めず、`"calling subagent for <description>"`（呼び出し時）・`"回答が来ました。<内容>"`（結果受信時）という事実のみ記録する |

`limit`引数（0以上の整数、または`none`）で`user`/`agent`各行の文字数上限を指定する。超過分は`...(他N文字)`に切り詰められる（`calling subagent for`/`回答が来ました。`のプレフィックスは切り詰め対象外、本文のみ切り詰める）。

対象範囲：`~/.claude/projects/**/*.jsonl`全件を、対象日の暦日（00:00〜24:00、Asia/Tokyo）に含まれる`turn_duration`イベントでフィルタする。`subagents/`配下のログファイルは除外する（フォークされたサブエージェント自身のログであり、トップレベルの記録ではないため）。複数の異なるセッションファイルにまたがるturnも、timestamp昇順にマージして1つのJSON配列として出力する。

### 12. 永続化と、Jira投稿・sync・validateの交換形式対応（決定・実装済み、2026-08-25）

#### 課題

`worklog.tsv`は「全期間を1ファイルに蓄積する」役割を担っていたが、これを廃止すると「投稿済み・人間が編集確定させた記録」を永続化する場所が無くなる（`worklog_session_infer.sh`のセグメントJSONはあくまで一時出力）。

#### 決定した設計

- **`bin/worklog/log/<date>.json`**（例: `bin/worklog/log/2026-08-24.json`）を、確定・投稿済みセグメントの永続保存場所とする。git管理下。`worklog.tsv`が担っていた「全期間の蓄積」の役割を、1日1ファイルに分割して引き継ぐ
- posted状態は各セグメント要素の`posted_at`フィールドとしてファイル自体に持たせる（`worklog.tsv`時代の`posted_at`列と同じ発想）
- 一連のワークフロー（AI Agentが必ず守るべき手順として`instructions_to_ai_agent.md`へ切り出し済み。特に「人間が編集」チェックポイントを省略しないこと）

#### 実装物

- `bin/worklog/worklog_lint.sh` / `.py`（新規）：`worklog_tsv_validate.sh`の後継。セグメントJSON配列をstdinから読み、必須フィールド・date/HH:MM形式・start<end・durationの整合性・同一date内の時間帯重複・date/start昇順・posted_atの形式を検査する読み取り専用フィルタ。問題なければ配列をそのままstdoutへ通す
- `bin/worklog/worklog_jira_post_batch.sh <file> [--dry-run] [--confirm]` / `.py`：`worklog.tsv`ではなく`<file>`（セグメントJSON）を読み書きするよう書き換え。`posted_at`が空/無い要素を対象にPOSTし、成功した要素だけ`posted_at`を設定して同じファイルへ書き戻す
- `bin/worklog/worklog_jira_sync.sh <date> <file> [--dry-run] [--confirm]` / `.py`：`<file>`引数を追加（`worklog.tsv`固定参照をやめた）。ロジック（issueごとの1:1対応付け、2026-08-24修正済みの「投稿済み要素も含めて全ローカル要素を見る」バグ修正）は踏襲。`<file>`が存在しなければ新規作成する
- `bin/worklog/worklog_jira_validate.sh <from_date> <to_date>` / `.py`：シグネチャは変更なし。「local」データの参照先を`worklog.tsv`から`bin/worklog/log/<date>.json`（範囲内の日付ごとに存在すれば読み、無ければその日はlocalデータ無し扱い）に変更。freeeは引き続き「その日の勤怠区分（勤務/休日/休暇）を読む」目的でのみ使用しており（作業時間の外枠としては使わない）、アーキテクチャ節の方針転換と矛盾しない
- `worklog.tsv` / `worklog_tsv.py` / `worklog_tsv_validate.py` / `.sh`、および`worklog_entry_start.sh`/`.py`・`worklog_entry_end.sh`/`.py`（§7参照）を削除。削除前に全参照元が上記書き換え済みツールのみであることを確認済み
- `worklog.tsv`の既存データ（2026-08-17〜21分、全行`posted_at`埋まっており未投稿分なし）は`bin/worklog/log/`へ移行しなかった。`worklog_jira_validate.sh`で該当期間を検査した結果、Jira側の実績と完全に一致し要確認0件だったため（Jira自体が既にその期間の正本として機能しており、ローカル移行の実益が無いと判断）

### 13. 自分の担当チケット一覧（決定・実装済み、2026-08-27）

「次は？」フローの候補生成（未決事項）に使える部品として、自分にアサインされた未完了チケットを一覧するツールを実装した。

`bin/worklog/worklog_jira_ticket_list.sh <tsv|json>` / `.py`（読み取り専用）：JQL `assignee = currentUser() AND statusCategory != Done ORDER BY status ASC, updated DESC` で検索し、`key, status, summary, url`を指定形式（TSVまたはJSON配列）で標準出力する。

## 未決事項

- **freeeとの関係の反転**（交換形式から「もっともらしい打刻」を生成する）：決定論的に機械化できないため、本worklogシステムの他の部分が完成してから着手する
- **`worklog_session_infer.sh`のnote初期値の質**：`/compact`等のスラッシュコマンドのエコーがnoteの初期値に採用されてしまうケースがある（§10「新方式」実測参照）。除外対象を`<system-reminder>`以外にも広げるか検討の余地あり
- **「次は？」フローと候補生成、`worklog_lint.sh`の検査項目拡張**：現状の`worklog_lint.sh`は基本的な形式チェックのみ。ticketが実在のJiraチケット形式か、重複postingの兆候があるか等、検査項目を今後拡張する余地がある
- 「次は？」で提示する候補の生成ロジック。`cwd => issue => ticket`の高速な順方向解決は決定・実装済み（§9）。残る論点は、どのrepo/issueを候補として提示するか（JQLの絞り込み条件、例えば担当中チケットや直近更新分）と、リポジトリに対応付けられていないcwdのセッション（**野良セッション**と呼ぶ。用語決定、2026-08-21）・未同期issueのフォールバック
- `config.json`のスキーマ（`MAX_TODO_COUNT`以外に何を持たせるか）
