# AI Agentへの指示（worklogシステム）

design.mdから切り出した、AI Agentが必ず守るべき操作手順。

## 日次worklog登録のワークフロー

```bash
worklog_session_turns_list.sh <date> none | worklog_session_infer.sh > bin/worklog/log/<date>.json
# 人間がVSCode等で編集(ticket再割当・区間分割・note修正)
worklog_lint.sh < bin/worklog/log/<date>.json
worklog_jira_post_batch.sh bin/worklog/log/<date>.json --confirm
```

- AI Agentは `bin/worklog/log/<date>.json` を生成・編集した後、**人間の確認を経ずに** `worklog_jira_post_batch.sh` を実行してはならない。区間分割・ticket再割当てをAI Agentが提案する場合も、投稿前に必ず人間の目視確認とgoサインを得ること。
- ticket再割当てが必要な場合は、`worklog_session_turns_guess_ticket.sh <rules_file>` の出力を人間が目視確認した上で反映する。
- `worklog_lint.sh`は投稿前に必ず通すこと(省略しない)。
