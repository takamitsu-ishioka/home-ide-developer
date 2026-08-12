#!/usr/bin/env bash
set -euo pipefail

# freee のアクセストークンを取得する手順書 兼 実行スクリプト。
# GUI操作の手順をスクショで残さず、実行可能な形でここに残す方針に従う。
# この手順は初回のみ実行する。
#
# --- 手順 ---
#
# 0. cp .env.template .env
#
# 1. アプリを作成して client_id / client_secret を取得する(手動)
#    a. https://app.secure.freee.co.jp/developers にログイン
#    b. 「従業員として所属する事業所」を選択する
#       (顧問先アドバイザーとしての事業所ではアプリを作成できない)
#    c. 「アプリ管理」→「新規追加」でアプリ名・概要を入力して作成
#    d. 発行された client_id / client_secret を .env の
#       FREEE_CLIENT_ID / FREEE_CLIENT_SECRET に貼る
#    e. コールバックURL欄の初期値が urn:ietf:wg:oauth:2.0:oob であることを確認する
#       (実在するURLではなく、認可コードを画面にそのまま表示させるための予約値)
#    f. 利用するAPIで「人事労務API」を有効化する。「人事労務」は無暗に項目数が多いので全部チェックでいいかも（未検証）。
#    g. WebGUIを閉じる。以下のステップはターミナルで実行します。
#
# 2. このスクリプトを実行する(このステップ以降は自動)
#    a. スクリプトが認可用URLを表示するので、ブラウザでそのURLを開く
#    b. freeeにログイン → 事業所選択 → 「許可する」をクリックすると
#       画面に認可コード(使い捨て・数分で失効)が表示される
#    c. その認可コードをスクリプトのプロンプトに貼り付けてEnter
#    d. スクリプトが認可コードを access_token / refresh_token に交換し、
#       .env の FREEE_ACCESS_TOKEN / FREEE_REFRESH_TOKEN を自動で書き換える
#
# 3. 以降の運用
#    access_token は6時間で失効するので、切れたら refresh_access_token.sh を
#    実行する(refresh_token も1回使うと無効になるため、これも自動で書き戻される)。
#    認可コードの再取得(このスクリプトの再実行)は refresh_token 自体が
#    失効した場合(90日)だけでよい。
#
# 注：このスクリプトは Claude Code で生成したそのまま。一度もテストしていません。
#
# 石岡（このスクリプト群の作成者）の感想
# 何と言うか…。金庫のカギを保管する金庫のカギを保管する金庫の(以下省略)。みたいな世界ですね（笑）。

SCRIPT=$(basename "$0")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_FILE="${FREEE_ENV_FILE:-$SCRIPT_DIR/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "$SCRIPT: $ENV_FILE not found. Copy $SCRIPT_DIR/.env.template to $ENV_FILE and fill it in." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [ -z "${FREEE_CLIENT_ID:-}" ] || [ -z "${FREEE_CLIENT_SECRET:-}" ]; then
  echo "$SCRIPT: FREEE_CLIENT_ID / FREEE_CLIENT_SECRET is not set (check $ENV_FILE). See step 1 in this script's comments." >&2
  exit 1
fi

STATE="$(date +%s)"
AUTHORIZE_URL="https://accounts.secure.freee.co.jp/public_api/authorize?response_type=code&client_id=${FREEE_CLIENT_ID}&redirect_uri=urn:ietf:wg:oauth:2.0:oob&state=${STATE}&prompt=select_company"

echo "以下のURLをブラウザで開き、ログイン → 事業所選択 → 「許可する」をクリックしてください。" >&2
echo "$AUTHORIZE_URL" >&2
echo >&2
read -r -p "画面に表示された認可コードを貼り付けてEnter: " AUTH_CODE

if [ -z "$AUTH_CODE" ]; then
  echo "$SCRIPT: 認可コードが空です" >&2
  exit 1
fi

curl -sf -X POST \
  -H "Content-Type:application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=${FREEE_CLIENT_ID}" \
  -d "client_secret=${FREEE_CLIENT_SECRET}" \
  -d "code=${AUTH_CODE}" \
  -d "redirect_uri=urn:ietf:wg:oauth:2.0:oob" \
  "https://accounts.secure.freee.co.jp/public_api/token" \
  | ENV_FILE="$ENV_FILE" python3 -c '
import json
import os
import sys
from pathlib import Path

env_path = Path(os.environ["ENV_FILE"])
body = json.load(sys.stdin)
if "access_token" not in body:
    print(f"get_credentials.sh: token exchange failed: {body}", file=sys.stderr)
    sys.exit(1)

updates = {
    "FREEE_ACCESS_TOKEN": body["access_token"],
    "FREEE_REFRESH_TOKEN": body["refresh_token"],
}

lines = env_path.read_text().splitlines(keepends=True)
seen = set()
new_lines = []
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in stripped:
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            seen.add(key)
            continue
    new_lines.append(line)
for key, value in updates.items():
    if key not in seen:
        new_lines.append(f"{key}={value}\n")
env_path.write_text("".join(new_lines))
print(f"get_credentials.sh: updated {env_path}", file=sys.stderr)
'
