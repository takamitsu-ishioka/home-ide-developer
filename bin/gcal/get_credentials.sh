#!/usr/bin/env bash
set -euo pipefail

# Google CalendarのOAuthトークンを取得する手順書 兼 実行スクリプト。
# GUI操作の手順をスクショで残さず、実行可能な形でここに残す方針に従う(bin/freee/get_credentials.shと同型)。
# この手順は初回のみ実行する。ループバックリダイレクト方式(RFC 8252)を使うため、
# ローカルに一時的なHTTPサーバーを立てて認可コードを受け取る(WSL2はlocalhostが
# Windows側と自動で相互転送されるため、ブラウザはWindows側の既定ブラウザで問題ない)。
#
# --- 手順 ---
#
# 0. cp .env.template .env
#
# 1. OAuthクライアントを作成する(手動)
#    a. https://console.cloud.google.com/ にログインし、プロジェクトを作成(または既存を選択)
#    b. 「APIとサービス」→「ライブラリ」で "Google Calendar API" を検索して有効化
#    c. 「APIとサービス」→「OAuth同意画面」で外部/テスト、自分のGoogleアカウントを
#       テストユーザーとして追加(公開審査を受けない限りテストユーザーのみ利用可能)
#    d. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
#       アプリケーションの種類: 「デスクトップ アプリ」
#       (「テレビと入力が限られたデバイス」はcalendar系スコープを扱えず invalid_scope になるため不可)
#    e. 発行されたクライアントID/シークレットを.envの
#       GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET に貼る
#
# 2. このスクリプトを実行する(このステップ以降は自動)
#    a. スクリプトが認可用URLを表示するので、ブラウザでそのURLを開く
#    b. Googleにログイン→「許可」をクリックする(ブラウザには「このタブは閉じて構いません」と表示される)
#    c. スクリプトがローカルサーバーでリダイレクトを受け取り、自動で認可コードを
#       access_token/refresh_tokenに交換して.envのGOOGLE_ACCESS_TOKEN/GOOGLE_REFRESH_TOKENに書き込む
#
# 3. 以降の運用
#    access_tokenは短時間(通常1時間)で失効する。呼び出し側スクリプトは401を検知したら
#    refresh_access_token.shで自動更新する(gcal_api.py参照)。Googleのrefresh_tokenは
#    freeeと違い1回使っても無効化されない(ローテーションしない)ため、再度このスクリプトを
#    実行する必要があるのはrefresh_token自体が失効・取り消しされた場合のみ。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT=$(basename "${BASH_SOURCE[0]}")

ENV_FILE="${GCAL_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 "$SCRIPT_DIR/get_credentials.py"
