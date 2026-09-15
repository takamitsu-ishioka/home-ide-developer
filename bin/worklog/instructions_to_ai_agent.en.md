# Instructions to the AI Agent (worklog system)

The operating procedure the AI Agent must follow, cut out of design.md.

## Daily worklog registration workflow

```bash
worklog_session_turns_list.sh <date> none | worklog_session_infer.sh > bin/worklog/log/<date>.json
# a human edits it (VSCode etc.) — reassign tickets, split segments, fix notes
worklog_lint.sh < bin/worklog/log/<date>.json
worklog_jira_post_batch.sh bin/worklog/log/<date>.json --confirm
```

- After generating or editing `bin/worklog/log/<date>.json`, the AI Agent must **never** run `worklog_jira_post_batch.sh` without a human review first. Even when the AI Agent proposes segment splits or ticket reassignments, it must get explicit human sign-off before posting.
- When ticket reassignment is needed, a human must visually check the output of `worklog_session_turns_guess_ticket.sh <rules_file>` before it is applied.
- Always run the output through `worklog_lint.sh` before posting — never skip it.
