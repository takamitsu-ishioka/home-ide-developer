---
id: KB-000002
tags:
  - Codex
  - ntfy
  - notification
  - smartphone
  - privacy
related: []
---

# Codexのnotifyは会話ペイロードを固定文へ変換してntfyへ安全に中継できる

## 症状

Codexの作業終了を、PCから離れているユーザーのスマートフォンへ通知したい。
Codexの`notify`コマンドにはJSONが渡され、そのJSONには入力メッセージや最終応答が
含まれ得るため、そのまま外部通知サービスへ送ると個人情報やソースコードが漏れる。

## 原因（確定）

Codexのユーザー設定`~/.codex/config.toml`にある`notify`は、現在
`agent-turn-complete`イベントで外部コマンドを実行し、JSONを引数として渡す。
したがって、JSONを直接送信せず、イベント種別だけを検査して固定文へ変換する
アダプターを挟めば、完了通知と情報非漏洩を両立できる。

## 対処 / 復旧手順

1. `~/bin/ntfy/.env.template`を同じ場所の`.env`へコピーする。
2. `openssl rand -hex 24`でトピックを作り、ユーザーが`.env`へ記入する。
3. `chmod 600 ~/bin/ntfy/.env`を実行する。
4. スマートフォンのntfyアプリで同じトピックを購読する。
5. `~/bin/ntfy/ntfy_notification_send.sh 'テスト通知'`で受信を確認する。
6. ユーザーの承認後、`~/.codex/config.toml`へ次を追加する。

```toml
notify = ["/home/developer/bin/ntfy/codex_turn_notification_send.sh"]
```

## 検証方法

一時ディレクトリのダミー`.env`と偽の`curl`を使い、次を確認済み。

- 引数と標準入力の両方から送信できる。
- `--dry-run`では送信しない。
- `agent-turn-complete`だけを通知する。
- Codex JSON中の`input-messages`と`last-assistant-message`を通知やログへ出さない。
- ntfy送信失敗がCodexの完了済みターンへ波及しない。
- bash構文、Python構文、ファイル実行権限が正しい。

スマートフォン実機での受信は、ユーザーによる秘密トピック設定後に確認する。

## 備考

- ntfy.shは標準でメッセージを一時キャッシュするため、スマートフォンの一時的な
  ネットワーク切断から復帰した後も受信できる。
- 公開サーバーで認証を使わない場合、トピック名が事実上の秘密になる。
- 通知本文には固定文だけを使い、作業内容、パス、コード、認証情報を含めない。
