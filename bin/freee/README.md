# freee work records helper

freee人事労務APIから指定年月の勤務実績を取得し、勤務した日の平均勤務時間を計算する小さなツールです。

## WSL Ubuntuでの準備

```bash
sudo apt update
sudo apt install -y curl python3 shellcheck
cp .env.template .env
chmod +x *.sh *.py
```

`.env` に以下を設定してください。

```env
FREEE_ACCESS_TOKEN=...
FREEE_EMPLOYEE_ID=...
FREEE_CLIENT_ID=...
FREEE_CLIENT_SECRET=...
FREEE_REFRESH_TOKEN=...
```

## 使い方

```bash
./fetch_work_records.sh 2026 7 | ./calc_avg_work_time.py
```

アクセストークンが期限切れになった場合は、次を実行して `.env` を更新します。

```bash
./refresh_access_token.sh
```

初回の認可コード取得が必要な場合は、次を実行します。

```bash
./get_credentials.sh
```

## 確認

```bash
shellcheck fetch_work_records.sh refresh_access_token.sh get_credentials.sh
python3 -m py_compile fetch_work_records.py calc_avg_work_time.py refresh_access_token.py
```
