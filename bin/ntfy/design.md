# スマホ通知機構の設計

## 目的

エージェントの作業終了やシェルスクリプトの終了をきっかけに、任意の文字列をユーザーのスマートフォンへ通知する。

初期実装では、無料で利用を開始でき、アカウント登録やAPIキーを必要としない`ntfy.sh`の公開サーバーを使用する。

## 基本方針

- 通知送信処理を`~/bin/ntfy/ntfy_notification_send.sh`へ集約する。
- 呼び出し側はntfyのURLや通信方式を意識しない。
- 通知本文はコマンドライン引数または標準入力から受け取る。
- トピック名は推測困難なランダム値とし、Git管理しない。
- 通知には個人情報、機密情報、認証情報、ソースコードを含めない。
- 通知失敗を理由に、本来の作業結果や終了コードを変更しない。
- エージェントの設定ファイルは、ユーザーの明示的な承認を得てから変更する。

## 構成

```text
~/bin/ntfy/
├── design.md                          # 本設計書
├── ntfy_notification_send.sh          # 任意の文字列をntfyへ送る
├── codex_turn_notification_send.sh    # Codex通知用アダプター
├── codex_turn_notification_message.py # Codex JSONから安全な固定文を作る
├── .env.template                      # 設定例
└── .env                               # 実設定。権限600、Git管理外
```

実際の設定ファイルは、次の形式を想定する。

```bash
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=十分に長いランダムなトピック名
NTFY_TITLE=作業通知
NTFY_PRIORITY=default
```

## コマンド仕様

### 引数から送信

```bash
~/bin/ntfy/ntfy_notification_send.sh 'タイトル画像の生成が完了しました'
```

### 標準入力から送信

```bash
printf '%s\n' 'バックアップが完了しました' | ~/bin/ntfy/ntfy_notification_send.sh
```

引数と標準入力の両方が指定された場合は引数を優先する。どちらも空の場合は使用法を表示して終了する。

HTTP送信には`curl`を使用し、本文は`--data-binary`で送る。通知タイトルはHTTPヘッダーで指定する。初期設定ではntfyの標準キャッシュを使用し、スマートフォンが一時的にオフラインでも通知を受け取れるようにする。

## 終了コード

- `0`: ntfyが通知を受理した。
- `1`: 引数不足、設定不足、通信失敗など。

通知を付加機能として呼び出す場合は、呼び出し元の終了コードを壊さないようにする。

```bash
status=$?
~/bin/ntfy/ntfy_notification_send.sh "処理終了: exit=$status" || true
exit "$status"
```

## エージェントとの連携

Codexでは、ユーザー設定`~/.codex/config.toml`へ次を追加する。Codexの`notify`は
`agent-turn-complete`時にJSONをコマンドライン引数として渡す。JSONには会話内容が含まれ得るため、
アダプターはイベント種別だけを読み、スマートフォンには固定文だけを送る。

```toml
notify = ["/home/developer/bin/ntfy/codex_turn_notification_send.sh"]
```

この設定ファイルの変更は、ユーザーの明示的な承認後に行う。

Claude Codeでは`Stop` hookから`~/bin/ntfy/ntfy_notification_send.sh`を呼び出す。`Stop`は依頼全体の完成時だけでなく応答終了時にも発火するため、通知文は「作業完了」ではなく「応答終了」または「確認してください」とする。

設定例は次のとおり。ただし、既存の`~/.claude/settings.json`を確認し、現在の設定を保持したまま追加する。

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/bin/ntfy/ntfy_notification_send.sh 'Claude Codeの応答が終了しました' || true"
          }
        ]
      }
    ]
  }
}
```

ほかのエージェントについては、公式の終了hookが利用できる場合は同じ送信コマンドを登録する。終了hookがない場合は、CLIを起動するラッパースクリプトから終了コードを通知する。

## 通常のスクリプトとの連携

成功時だけ通知する例：

```bash
run_the_job
~/bin/ntfy/ntfy_notification_send.sh '処理が正常終了しました' || true
```

成功・失敗の両方を通知する例：

```bash
if run_the_job; then
  ~/bin/ntfy/ntfy_notification_send.sh '処理が正常終了しました' || true
else
  status=$?
  ~/bin/ntfy/ntfy_notification_send.sh "処理に失敗しました: exit=$status" || true
  exit "$status"
fi
```

## セキュリティとプライバシー

認証を使用しない場合、トピック名を知っている人は通知を購読・投稿できる。したがって、トピック名を事実上の秘密文字列として扱う。

- トピック名は暗号学的乱数から生成し、48桁程度の16進文字列を含める。
- トピック名をソースコード、設計書、Git、ログへ記録しない。
- 設定ファイルの権限を`600`にする。
- 通知本文は「処理名」「成功・失敗」「確認が必要」程度に限定する。
- より強い秘匿性が必要になった場合は、ntfyの認証機能またはセルフホストへ移行する。

## 導入手順と担当

agent:

1. `~/bin/ntfy/ntfy_notification_send.sh`、Codex用アダプター、`.env.template`を作成する。
2. ユーザーが推測困難なトピック名を生成する。
3. ユーザーが`.env.template`を`.env`へコピーし、トピックを書き、権限`600`にする。
4. テスト通知を送信し、ntfyが受理したことを確認する。
5. ユーザーから受信確認を得る。
6. ユーザーの明示的な許可後に、対象エージェントの終了hookを設定する。
7. 成功通知、失敗通知、空メッセージ、通信失敗時の挙動を検査する。

user:

1. スマートフォンへntfyアプリをインストールする。
2. エージェントが生成したトピック名をアプリで購読する。
3. テスト通知を受信できたか回答する。
4. 通知音、バイブレーション、通知優先度をスマートフォン側で調整する。
5. エージェント終了hookを設定してよいか判断し、対象を指定する。

## 完了条件

- `~/bin/ntfy/ntfy_notification_send.sh '任意の文字列'`でスマートフォンへ通知できる。
- 通知できない場合も、呼び出し元の本来の終了コードを保持できる。
- トピック名がGit管理されず、設定ファイルが権限`600`になっている。
- ユーザーがテスト通知の受信を確認している。
- 許可されたエージェントまたはスクリプトからのみ自動通知される。
