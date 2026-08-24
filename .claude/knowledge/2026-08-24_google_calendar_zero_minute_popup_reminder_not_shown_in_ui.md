---
id: KB-000001
tags:
  - Google Calendar
  - gcal
  - reminders
  - popup
  - UI
related: []
---

# Google CalendarのUIは「0分前」popup通知を表示しない（API上は正しく保存されている）

出典: 2026-08-24、`~/bin/gcal/gcal_event_add.sh` でCLIから予定を登録したセッション。
ユーザーが「GUIで登録した予定は通知時刻が見えるが、CLIのやつは見えない」と報告。

## 症状

`gcal_event_add.sh` で `reminder=00:00`（開始時刻ちょうど＝0分前）を指定して登録した予定を
Google CalendarのGUI（Web/アプリ）で開いても、通知（リマインダー）欄が表示されない。
同じ手順で `reminder=00:10`（10分前）を指定した予定は、GUI上に「10分前」と正しく表示される。

## 原因（確定 — 実機で切り分け済み）

`gcal_event_get.sh` でAPIレスポンスを直接確認したところ、`reminder=00:00`の予定でも
`popup:00:00` がAPI側には正しく保存されていた（`reminders.overrides = [{"method":"popup","minutes":0}]`）。
つまり `bin/gcal/gcal_event_add.py` のバグではなく、**Google Calendar自身のクライアントUIが
「0分前（開始時刻ちょうど）」のpopup通知だけを表示しない**という制約/挙動である。

10分前の同条件テスト（同じスクリプト・同じフロー、`reminder=00:10`のみ変更）ではGUIに
正しく表示されたため、「CLI作成イベント全般の表示問題」ではなく「0分前という値そのもの」が
原因であることを切り分け済み。

## 対処 / 復旧手順

- 「開始時刻ちょうどに通知してほしい」場合でも、GUIで確認したいなら `reminder` を `00:00`
  ではなく `00:01`（1分前）以上にする。
- どうしても0分前が必要な場合は、通知が来ること自体はGoogle側で機能する（popup通知は届く）
  可能性が高いが未検証。GUI上の「見える化」だけができない点に注意。
- 既存の0分前予定を作り直す場合は `gcal_event_reminder_delete.sh` で `00:00` を削除し、
  `gcal_event_reminder_add.sh` で別の値を追加する。

## 検証方法

```bash
cd ~/bin/gcal
./gcal_event_add.sh TOMORROW 15:00 15:30 00:10 "テスト:通知表示確認"
# → GUIで開いて「10分前」が表示されることを確認
./gcal_event_get.sh <id>   # reminders列が popup:00:10 になっていることを確認
```

## 備考

- `bin/gcal/gcal_event_add.py` の `build_reminders()` は `minutes=0` でも
  `{"useDefault": False, "overrides": [{"method": "popup", "minutes": 0}]}` を正しく組み立てており、
  修正不要。あくまでGoogle Calendar側UIの表示仕様の問題。
- 未検証: モバイルアプリ/他ブラウザでも同じ挙動か。時間があれば別環境でも確認したい。
