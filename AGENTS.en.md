# ntfy completion notification

For a request involving file changes, command execution, or external-service operations, run the following command exactly once immediately before the final response, and only after all requested work has genuinely completed with no remaining work.

```bash
/home/developer/bin/ntfy/ntfy_notification_send.sh 'Codexの作業が完了しました。確認してください。'
```

Do not notify for intermediate updates, status reports, clarification questions, ordinary conversation, answer-only requests, failures, incomplete work, or blocked work.
Notification success or failure does not change the underlying task result. If delivery fails, mention the failure in the final response.
