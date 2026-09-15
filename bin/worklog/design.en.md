# worklog Design Document

## Purpose (redefined 2026-08-25)

To eliminate the act of "work reporting" itself. This design does not assume an operating model where a human consciously declares "I'm now starting work on ticket X" before starting work.

Consolidating onto `integrated-work-environment` (always working from the single `~/developer` repository) means that nearly all work activity already gets recorded in Claude Code session logs. This is analyzed after the fact to identify the correspondence between

- what the user was working on at a given point in time
- a GitHub issue
- a Jira ticket

so that the daily work-time record shown on [Jira dashboard 10011](https://dominosvr.atlassian.net/jira/dashboards/10011) can be generated with nothing more than human review and correction.

Source: `tmp/work.md` (as of 2026-08-14). The purpose itself was redefined on 2026-08-25 (see the architecture section below).

## Architecture: SSoT, exchange format, pipeline (decided, 2026-08-25)

- **SSoT (Single Source of Truth)**: raw Claude Code session log data (`~/.claude/projects/**/*.jsonl`). Pre-existing primary information that neither the human nor the AI rewrites.
- **Exchange format**: a JSON array. Turn-level records (one prompt : one response) produced by `worklog_session_turns_list.sh` (schema in §11).
- **TSV is deprecated in principle.** Human review/editing has been confirmed to be perfectly practical using VSCode's JSON editor plus search (a full day's `worklog_session_turns_list.sh` output, formatted with `json_pretty_print.sh`, was edited without issue at a scale of a few hundred lines).
- **Pipeline**:
  ```
  SSoT(session logs) => exchange format(JSON) => human + lint.sh => exchange format(validated) => downstream tools
  ```
  "human + lint.sh" refers to the step where a human directly edits the JSON (reassigning tickets, splitting segments, fixing notes, etc.) and then runs it through a mechanical validity check (a lint tool — not yet implemented, see "Open items" below).

### Relationship to freee (decided, 2026-08-25)

Clock-punch data (freee) is **no longer used as the "frame" bounding work time**. In reality it's not unusual for someone to be on a break and then get pulled into different work via a Teams call — a clock punch doesn't accurately reflect what actually happened; it's little more than a "plausible-looking fiction." Therefore:

- Generating the exchange format and aggregating into per-ticket segments (§10, §11) does not depend on freee. The day's outer bound is simply the first turn through the last turn actually recorded in the session log that day.
- Conversely, we may eventually want to **generate a "plausible-looking clock punch"** from the exchange format (making freee a secondary artifact derived from it). But this can't be mechanized deterministically — it requires AI judgment. This will be considered separately, after the rest of the worklog system is complete (open item).

## Design principle

Following CLAUDE.md's policy, minimize reliance on AI inference (which is variable, slow, and costs money), and execute as much processing as possible with deterministic scripts ([[feedback_ai_as_parts_maker]]). Where AI judgment is unavoidable (e.g. identifying the correspondence between work activity and an issue/ticket), the AI proposes candidates, but a human always makes the final decision.

## Overall design

### 1. Declaring the work context at session start (decided)

(Note: this is really `bin/claude/claude_launch.sh`. §9 implemented `cwd_chain_show.sh` as a stderr display at launch, but that's purely for the human to read — the mechanism described below, passing context as Claude's first message, is still not implemented.)

Pass the work context as a bare argument (no `-p`) when launching `claude_session_launch.sh`.

```bash
claude_session_launch.sh "{repo: integrated-work-environment, issue: none}"
```

`-p`/`--print` is a non-interactive, one-shot-response mode, so it's not used. The bare argument is delivered as the first message of the interactive session, and the conversation continues from there.

### 2. The "what's next?" flow during a session (decided)

When the user asks "what should I do next?", the AI scans back through the session and presents up to `MAX_TODO_COUNT` (configured in `~/bin/worklog/config.json`) undecided work candidates in the form `{repo, issue, note}`. The user confirms one by its number.

```
user: What's next?
claude:
  1.
    repo: foobar
    issue: bug/123 "..."
    note: ...
  2.
    repo: none (defaults to integrated-work-environment)
    issue: none
    note: ...
user: 1, please.
```

The moment the user confirms a number, or declares the end of work (e.g. "that's it for today"), **Claude calls `worklog_entry_start.sh` / `worklog_entry_end.sh` (see §7)**. There's no assumption that the user runs these directly from a shell themselves — natural-language exchange is the trigger ([[feedback_ai_as_parts_maker]]: the AI calls a scripted operation rather than performing API/file work directly). That said, the scripts themselves behave identically regardless of who invokes them, so manual execution isn't precluded.

**Argument visibility (decided)**: whenever Claude calls these on its own, it must state in one line of on-screen chat text, immediately before the call, exactly which command and arguments it's about to run. The scripts themselves also print an `入力:` (input) block to stderr before writing anything (§7), but stating it in Claude's own speech as well ensures the user can always confirm "what's about to run" from the chat text alone, even when the tool-call UI is collapsed/summarized.

The concrete cues for candidate generation (list of assigned Jira tickets / open PRs / session content, etc.) are still undecided (see "Open items" below).

(Note: this flow and the `worklog_entry_start/end.sh` punch-based approach remain a separate lineage from the purpose redefined above — "eliminating the act of work reporting." See "Open items" for the reconsideration of their role.)

### 3. Storage location and naming (decided)

Keep executables, config, and accumulated data together under `~/bin/worklog/`.

- `~/bin/freee/` already has `time_clock_punch.log` (a non-executable, git-tracked file) living alongside its scripts, an existing precedent in this repo for mixing executables and data.
- This also matches the "tool system with `~/bin` as the single entry point" philosophy (CLAUDE.md).
- Why the name `worklog`: the ultimate destination, Jira itself, uses the terms "Log work" / "Worklog" as native feature names, so the correspondence "local worklog → Jira worklog" is clear from the name alone. `work_time` was avoided as it clashes confusingly with the existing `freee/` (attendance/work hours).

### 4. Investigating what actually backs Jira dashboard 10011 (decided, complete, updated with measurements)

Identified what data this dashboard is built from. This determines which API to write to.

#### Findings (display side)

Confirmed the text "Provided by Time Tracker · Contact support" at the bottom of the **"Timesheet" gadget** on dashboard 10011 (titled "作業時間"/"Work hours"). This is the standard label naming the Marketplace app, matching "Time Tracker (by Tempo Software)" shown in the gadget-add panel.

→ **Confirmed: the display (Timesheet gadget) is produced by Tempo's "Time Tracker" app (Tempo Timesheets).**

The dashboard also has a "Working time check (powered by freee API)" line, and its total matched. There may already be an in-house integration cross-checking the existing freee attendance system (`bin/freee/`) against Tempo's logged time.

#### Measured result (write side, 2026-08-20)

Initially assumed "display is Tempo-made → writing must go through a Tempo-only API," but this was wrong. Confirmed from source that the Domino Portal (`dominosoft-org/domino-portal`, `backend/routes/jira.ts`) achieves work-time logging using nothing but the **Jira-native worklog API** (`/rest/api/2/issue/{issueKey}/worklog`, Basic auth = each user's own email + Jira API token). Built a verification script, `worklog_jira_post.sh`, using the same approach. POSTing to GENERAL-451 actually showed up on the Timesheet gadget of dashboard 10011 **immediately** (confirmed by measurement — CLAUDE.md's DJC principle, "today's induction over yesterday's deduction," in practice).

→ **Confirmed: the write destination is the Jira-native worklog API (`/rest/api/2/issue/{id}/worklog`). No Tempo-side API (`api.tempo.io`) or Tempo-specific token is needed.** The display is Tempo-made, but it appears to be configured to ingest native Jira worklogs internally (caveat: as long as Tempo-specific fields like Tempo Account/Team aren't used).

This resolves the "waiting on Jira admin rights" blocker noted in "Open items" below. Implementation can proceed as soon as each user issues their own Jira API token.

#### Investigation method (reference: steps taken)

1. Check each gadget's "Edit gadget" menu (top right) for the JQL/report type it references.
2. If the gadget name/UI mentions "Tempo," it's likely using the Tempo app.
3. Check the "Provided by" text at the bottom of the gadget to directly identify the Marketplace app name.
4. Watching the Network tab in browser dev tools for API requests (`/rest/tempo-timesheets/...` or `api.tempo.io/...`) is also possible, but wasn't needed this time.
5. The look of a ticket's "Log work" dialog (standard Jira UI vs. Tempo's own UI) can also distinguish them.
6. With sufficient permissions, Jira admin → Apps → Manage apps lists installed apps.
7. **Don't conclude the write-side API from investigating the display side (1–6) alone. Actually POSTing one worklog via the Jira-native API and measuring whether it shows up on the dashboard is the most reliable method** (this is what ultimately settled the question here).

### 5. Daily session splitting (design/implementation target for this round)

#### Problem

`claude_session_launch.sh` always opened the session picker via `--resume`. Picking from that picker is left to manual human judgment, and if the same session keeps getting picked across day boundaries, it grows without bound. Also, the "what's next?" flow (scanning back through "today's session") requires sessions to already be split one-per-day. Leaving it to the picker isn't deterministic, which goes against CLAUDE.md's policy (execute as much as possible deterministically).

#### Design

1. At launch, search under `~/.claude/projects/` for a session whose `cwd` matches the current `pwd` and whose last-modified time (mtime) is "today" (local date).
   - The directory-name encoding scheme under `~/.claude/projects/<encoded-path>/` (e.g. `/` → `-`) is unofficial and unreliable, so it isn't trusted; instead, match by exact string comparison against the `cwd` field confirmed by measurement to exist on every line of each `.jsonl` file.
   - Exclude anything under `subagents/` (same treatment as `claude_session_to_markdown.py` / `claude_session_log_clean_up.py` — these are forked sub-agent conversations, not "today's main session").
2. Exactly one match → resume that session ID directly with `--resume <id>` (bypassing the picker entirely — fully deterministic).
3. Zero matches → launch a new session without `--resume` (a new session ID is generated automatically).
4. Multiple matches → pick the one with the latest mtime, and just list the rest to stderr (a deterministic tie-break; no human judgment involved).

#### Implementation (planned)

- `bin/claude_session_today_find.sh` / `.py`: a component that, given a cwd, looks up "today's" session ID. Expected to be reused not just by `claude_session_launch.sh` but also by the future "what's next?" flow (scanning back through today's session).
- Modify `bin/claude_session_launch.sh`: call the above and branch into `--resume <id>` or a fresh launch.

### 6. The actual API call for logging work (decided, implemented)

`worklog_jira_post.sh` / `.py`: takes `<issue_key> <started> <time_spent_seconds> <comment>` as arguments and POSTs to the Jira-native worklog API (`/rest/api/2/issue/{issueKey}/worklog`) using Basic auth (`JIRA_EMAIL` + `JIRA_API_TOKEN`, from `~/bin/worklog/.env`). Supports `--dry-run` (show what would be sent only) and `--confirm` (Y/n confirmation before sending). Confirmed on 2026-08-20 that a real POST to GENERAL-451 showed up on dashboard 10011 (see §4).

### 7. Storage format for confirmed work (retired, 2026-08-25)

This approach's premise — declaring work turn by turn — was fundamentally at odds with the purpose stated at the top of this document (eliminating the act of work reporting). `worklog_entry_start.sh`/`worklog_entry_end.sh`, `worklog_tsv.py`, and `worklog.tsv` were deleted at the same time the §10 "new approach" was introduced. What follows is the past design (kept for reference).

#### Design (old)

Use the existing `~/bin/worklog/worklog.tsv` (`date, start, end, duration, repo, issue, note, posted_at` TSV, git-tracked) as the accumulation target as-is. No new file is created.

The recording style follows the same "punch" approach as `bin/freee/time_clock_punch.sh` (clock_in/clock_out). The moment the user confirms a numbered candidate, all that's known is `{repo, issue, note, timestamp(=right now)}` — when that work will end is not yet known. So:

1. On confirmation (`worklog_entry_start.sh <repo> <issue> <note>`): if there's an immediately-preceding row with an unresolved (blank) `end`, close it by filling in `end` with the current time, then append a new row with `start=now, end=blank` (i.e. starting new work implicitly means the previous work has ended).
2. On declaring end-of-work (`worklog_entry_end.sh`): if there's an immediately-preceding row with an unresolved `end`, close it by filling in `end` with the current time. No new row is added. "That's it for today" in this very conversation is a concrete example of this trigger.

This means the user never has to consciously enter `start`/`end` — just the natural timing of saying "next is this" or "that's it for today" keeps `worklog.tsv` automatically in a consistent state (a sequence of segments with no overlaps or gaps).

#### Day-boundary guard (decided)

If the user leaves a session without saying anything, neither `worklog_entry_start.sh` nor `worklog_entry_end.sh` gets called, and an unresolved row is left dangling. If `worklog_entry_start.sh` (or `worklog_entry_end.sh`) is later called on some subsequent day, naively "closing it at the current time" would inject a duration into `worklog.tsv` with no bearing on reality (spanning a day boundary).

To prevent this, if the preceding unresolved row's `date` differs from today, **the script errors out instead of auto-closing it, and asks the user to fix it manually** (no new row is added either). No threshold like "how many hours counts as abnormal" is set. The judgment relies purely on the existing `date` field fact — whether it crosses a day boundary — nothing more (in line with CLAUDE.md's "explicitly flag any inference," this design avoids inference entirely rather than trying to guess-fill `end`).

Note that Claude Code has a `SessionEnd` hook (runs an external shell command when a session ends), but it wasn't confirmed from the documentation whether it reliably fires for an unintended exit (e.g. the user closing the terminal without saying anything). Relying on hook reliability would mean building in a failure mode for "what if it didn't fire." **This project therefore deliberately does not use the `SessionEnd` hook, relying solely on the day-boundary guard above.**

#### Implementation (deleted, 2026-08-25)

- `bin/worklog/worklog_entry_start.sh` / `.py`: takes `<repo> <issue> <note>`, closes the preceding unresolved row, then appends a new one. Has the day-boundary guard.
- `bin/worklog/worklog_entry_end.sh` / `.py`: no arguments. Only closes the preceding unresolved row. Has the day-boundary guard.
- `bin/worklog/worklog_tsv.py`: shared TSV read/write and day-boundary-guard logic (`is_stale`) used by both scripts.
- Both support `--dry-run` (show the change only). Since appending/rewriting the TSV is a side effect, the change is shown in one place before it happens (CLAUDE.md convention).

### 8. Resolving cwd => issue for the mmwave team (decided, implemented)

Of the "candidate generation logic" (open item), the resolution method for `cwd => issue`, scoped to mmwave-team development (`fl-mmwave`), has been decided.

#### Findings

- `dominosoft-org/mmwave_tools` is the predecessor to `integrated-work-environment` and is no longer used.
- Actual mmwave-team development happens in `uenoyama-dominosoft/fl-mmwave` (a different GitHub org, not `dominosoft-org`), cloned locally at `/mnt/c/Projects/mmwave/fl-mmwave`, with per-issue git worktrees under `/mnt/c/Projects/mmwave/worktrees/`.
- Jira tickets embed a reference to the GitHub issue in the `description` body, as an ADF heading "### GitHub Issue" followed by a paragraph containing the issue URL (not a remote link or custom field). Confirmed by measurement on MMWAVE-875.
- Worktree directory/branch naming had historically been inconsistent (`feature/#221-...`, `feature-448-...`, etc.).

#### Decided convention

Worktree directory names are always `<issue_number>-<slug>` (the `feature-`/`bug-` prefix words are dropped). Branch naming is left up to the team's broader conventions and isn't fixed by this design — it's passed explicitly as a script argument. "No issue, no development" is applied without exception; worktrees without an issue aren't allowed (issue creation is prompted instead). Existing non-conforming worktrees aren't renamed (the rule applies only to newly created ones going forward).

#### Implementation

- `bin/mmwave/worktree_create.sh <issue_number> <slug> <branch>` / `.py`: verifies the issue exists via `gh issue view` before running `git worktree add`. Since `issue_number` is a required argument, there's no way to invoke it without an issue. Reuses an existing branch if present, otherwise creates one fresh from `origin/develop`. Supports `--dry-run`/`--confirm`.
- `bin/mmwave/development_environment_lint.sh` / `.py`: read-only. Checks every worktree name under `/mnt/c/Projects/mmwave/worktrees/` against `^\d+-[a-z0-9-]+$`. Extended (alongside §9's cache) to surface the full `cwd => repo => issue => ticket` chain in one view (reports `ok`/`wrong_format`/`no_issue`/`no_ticket` as TSV, plus a `ticket_key` column). Exits non-zero on any violation.

### 9. Forward resolution of issue => ticket, and a fast composite of cwd => issue => ticket (decided, implemented)

#### Findings (correcting an earlier assumption)

§8 assumed the "### GitHub Issue" heading + following-paragraph-link format based on a single sample, MMWAVE-875. But measuring `project = MMWAVE AND updated >= -90d` (116 tickets) showed only 1 followed that format; the majority (successfully extracted from 91 of the 116) used a different one (inconsistent heading text like "作業内容"/"Work content", with the link as an ADF `inlineCard` node's `attrs.url`). It also turned out the referenced GitHub repo isn't only `fl-mmwave` — `mmwave_sensor_issues` and `mmwave_server_issues` also appear. A small number (2 measured) of tickets embed multiple GitHub issue links; in that case the first one in document order is used, with a stderr warning (explicitly flagging that a guess narrowed it to one, per CLAUDE.md policy).

This lesson led to reworking the extraction logic to not depend on a specific heading position — instead it scans the whole description for GitHub issue URLs (ADF `inlineCard`/`blockCard` urls, text link marks, or plain text, whichever form). A concrete case of a spec settled from a single sample being overturned later by real data (in DJC terms, preferring "induction from many" over "deduction from one").

#### Decided design

- Resolve issue => ticket via a local cache built up ahead of time, rather than scanning the full JQL result every time.
- Cache location: `~/.integrated-work-environment/issue_ticket_cache.json` (not `bin/worklog`-specific data — it's shared state referenced across multiple tools including `bin/worklog` and `bin/mmwave`, so it lives in a dedicated directory directly under home rather than under any one tool's directory. Excluded via `.gitignore` as secondary data regeneratable from Jira, etc.).
- Format: JSON (a nested structure `repo => issue_number => {ticket_key, synced_at}`). One repo maps to many issues, and JSON's nested structure expresses that more naturally than a flat list of TSV rows (also matches CLAUDE.md's guidance to use JSON for complex structures).
- Cache updates happen via an explicit, JQL-scoped `issue_ticket_sync.sh '<jql>'`. Idempotent, merge-style (other existing cache entries are preserved; only entries hit by this run are overwritten).
- cwd => issue reuses the existing worktree naming convention (§8) `<issue_number>-<slug>` as-is: repo name comes from `git remote get-url origin`, issue number from the leading digits of the directory name.
- `cwd_to_ticket.sh` composes the two above, so passing a cwd resolves a ticket_key end to end.
- `bin/mmwave/development_environment_lint.sh` (§8) was extended so the full `cwd => repo => issue => ticket` chain is visible in one view across every worktree under fl-mmwave (added a `no_ticket` status).

#### Implementation

- Location correction (2026-08-21): the following 4 scripts were originally placed under `bin/worklog/`, but turned out not to be worklog-specific — they're the `cwd => repo => issue => ticket` resolution logic itself (also referenced by mmwave's lint and by `claude_launch`'s statusLine display) — so they were moved to `bin/integrated_work_environment/`. Jira credentials (`.env`) remain solely stored at `bin/worklog/.env` and are shared from there. `bin/worklog/` retains only the scripts that operate on `worklog.tsv` itself: `worklog_entry_start/end.sh`, `worklog_jira_post.sh`, `worklog_jira_issue_get.sh`, `worklog_tsv.py`.
- `bin/integrated_work_environment/repo_issue_from_cwd.sh <cwd>` / `.py`: given a cwd (a git worktree), returns the repo name and issue number as TSV. Read-only.
- `bin/integrated_work_environment/issue_ticket_sync.sh <jql> [--dry-run] [--confirm]` / `.py`: extracts GitHub issue URLs from the description of tickets matched by the JQL, and merge-updates `~/.integrated-work-environment/issue_ticket_cache.json`. The only way to update the cache manually. Tickets that have a description but no discoverable GitHub issue link are listed to stderr (as `{JIRA_BASE_URL}/browse/{key}`) to prompt issue creation + linking (tickets with no description at all are excluded — judged unrelated to development).
- `bin/integrated_work_environment/ticket_from_issue.sh <repo> <issue_number>` / `.py`: looks up the cache and returns a ticket_key. Read-only.
- `bin/integrated_work_environment/cwd_to_ticket.sh <cwd>`: a thin bash script that just composes the two above (the composition itself is simple enough that no Python component was written — plain bash).
- `bin/mmwave/development_environment_lint.sh` (§8) was extended so that, for each `ok` worktree, it looks up the cache above and adds a `ticket_key` column, reporting `no_ticket` when not found.
- `bin/integrated_work_environment/cwd_chain_show.sh <cwd>`: shows the full `cwd => repo => issue => ticket` chain for a single cwd on one line. Read-only; doesn't error out even when resolution fails partway (a stray session / unsynced ticket) — it shows however much it could resolve. Since this is a cross-cutting tool that belongs to neither `bin/mmwave` nor `bin/worklog` exclusively, it lives in `bin/integrated_work_environment/`, newly created as an extension of the "avoid clutter directly under `bin`" policy (see the `.bashrc` comment).
- Integrated into `bin/claude/claude_launch.sh`: right after `session_name` is settled and just before `exec claude`, it prints `cwd_chain_show.sh "$(pwd)"` to stderr, so the chain state is quietly shown at launch exactly once regardless of which mode (`today`/`resume`/`new`/direct-specify/`--`-passthrough) was used to start.
- Measured: extracted GitHub issue links from 91 of 116 tickets matching `project = MMWAVE AND updated >= -90d`, confirming a mix of `fl-mmwave`/`mmwave_sensor_issues`/`mmwave_server_issues` repos. Running `development_environment_lint.sh` shows the chain state for all 7 worktrees at a glance: 3 `ok` (ticket_key resolved), 1 `no_ticket` (issue exists but no synced ticket), 2 `wrong_format`, 1 `no_issue`. `cwd_chain_show.sh` was also confirmed across all three patterns: successful resolution, unsynced ticket, and a stray session (outside any git repo / not matching worktree naming).

### 10. Inferring and bulk-registering per-ticket work time from session logs

#### Old approach (2026-08-24, archived)

The following is the past design, superseded on 2026-08-25 by the "new approach" (via the JSON exchange format) below. Kept for reference.

##### Problem

The punch-based approach (§7) assumes the user declares "next is this" every time the ticket switches, which doesn't handle days where that declaration was forgotten, or after-the-fact cleanup of work spanning multiple tickets. Meanwhile, the session log already records what was actually worked on (the trajectory of `cwd`).

##### Design history

Initially considered a "per-turn actual work time (summing `turn_duration` events)" approach, but handling away-from-keyboard/idle time turned out to require arbitrary threshold judgments and got complicated. On the user's suggestion, switched to **fixing freee's clock punches — a trustworthy measurement — as the day's outer bound, and simply splitting the interior only at `ticket_id` changes**. Under this approach, the notion of "idle time" never arises at all (the sum of start-to-end always equals freee's actual work-time figure exactly).

(2026-08-25 addendum: this was later reversed — freee's clock punch is a "plausible-looking fiction" that doesn't reflect reality and shouldn't be used as a bounding frame. See "New approach" below.)

##### Decided design (old)

1. Extract "turns" from the full day's session logs: `type:"system", subtype:"turn_duration"` events (primary information with `timestamp`/`cwd` directly attached, already computed per-turn by Claude Code itself).
2. Resolve each turn's `cwd` via the `cwd => repo => issue => ticket` chain (§9) into a `ticket_id`. When unresolvable (a stray session, an unsynced ticket), fall back to `ticket_id = GENERAL-451` (the default for miscellaneous work).
3. Sort the day's turns by timestamp ascending, and take the **first `clock_in` through the last `clock_out`** from freee's clock records (`bin/freee/time_clock_get.sh`) as the overall start/end.
4. Cut segment boundaries wherever `ticket_id` changes, and at break (`break_begin`/`break_end`) start/end points. A break segment gets the special value `ticket_id = "(休憩)"`, reverting to the pre-break `ticket_id` once the break ends.
5. Emit the result as candidate rows in the same schema as `worklog.tsv` (TSV, no side effects). A human reviews/edits them, then appends to `worklog.tsv` and bulk-submits via `worklog_jira_post_batch.sh`.

##### `worklog.tsv` schema extension (implemented, still in effect)

Added a `posted_at` column (6 columns → 7). Blank = not yet posted. Written after a bulk post, preventing double-registration on rerun. New rows added by manual punching (`worklog_entry_start.sh`) also write it as an empty string.

Addendum (2026-08-24): added a `duration` column to the right of `end` (7 columns → 8; order becomes `date, start, end, duration, repo, issue, note, posted_at`). Not new information — always derivable from `start`/`end` — but kept as a column so the duration is visible at a glance during review, without mental math, computed via `worklog_tsv.duration_hm()`. `worklog_entry_start.sh`/`worklog_entry_end.sh` compute and write it at the moment a row's `end` is finalized. Along the way, noticed `worklog_tsv.write_rows()` had been using `csv.DictWriter`'s default `lineterminator` (`\r\n`), which had been injecting CRLF into `worklog.tsv`; fixed by specifying `lineterminator="\n"` to match the rest of the repo's line endings.

##### Implementation (old; `worklog_session_infer.py` has since been replaced by the new approach)

- `bin/freee/time_clock_get.sh <date>` / `.py`: returns the given day's `time_clocks` (raw punch events) from freee as `type\tdatetime` TSV. Read-only (unused under the new approach).
- `bin/worklog/worklog_jira_api.py`: shared component extracted from `worklog_jira_post.py`, providing the actual Jira worklog POST logic (`post_worklog()`, `resolve_started()`). Used by both single and bulk posting (raises `JiraApiError`; the calling CLI decides how to exit).
- `bin/worklog/worklog_jira_post_batch.sh [--dry-run] [--confirm]` / `.py`: bulk-POSTs `worklog.tsv`'s unposted rows (`end` set and `posted_at` blank) to Jira. Records the outcome per row so one failure doesn't block the rest, writing `posted_at` only for rows that succeeded.
- `bin/worklog/worklog_jira_post.py`: refactored to use the shared component above (CLI contract/output unchanged).
- Measurement (2026-08-21, old approach): split into 6 segments from 85 turns and 1 break. Of 08:53–16:35 (matching freee's actual work time exactly), 2 segments were on the `fl-mmwave` worktree (`MMWAVE-922`), 1 was a break, and the rest were classified as `GENERAL-451` (work directly under `/home/developer` — a stray session).

##### Reverse-direction (Jira => worklog.tsv) sync and consistency check (implemented, still in effect)

While implementing/verifying `worklog_jira_post_batch.sh` (worklog.tsv => Jira), the user, looking at Jira dashboard 10011, noticed "the 17th already looks filled in and consistent." Investigation revealed that `worklog.tsv`'s unposted row (MMWAVE-787, 55 minutes) exactly matched an entry already present on the Jira side (also 55 minutes). This was likely already posted via a separate path (e.g. a one-off `worklog_jira_post.sh` run) while `posted_at` was left blank — bulk-posting as-is would have double-registered it. This is CLAUDE.md's DJC principle in action (comparing two independent sources — the Jira side and the worklog.tsv side — to detect a mismatch).

This prompted adding a reverse-sync tool and a period-based consistency checker.

- `bin/freee/work_record_get.sh <date>` / `.py`: returns the given day's `work_record` from freee (daily aggregate, including attendance classification such as `day_pattern`/`paid_holiday`/`is_absence`) as raw JSON. Read-only.
- `bin/worklog/worklog_jira_query.py`: shared component for Jira worklog search/fetch (used by both `worklog_jira_sync.py` and `worklog_jira_validate.py`). Searches matching issues via JQL (`worklogAuthor = currentUser() AND worklogDate >= ... AND worklogDate <= ...`), then fetches and filters each issue's worklog list by date range and self (`JIRA_EMAIL`).
- `bin/worklog/worklog_jira_sync.sh <date> [--dry-run] [--confirm]` / `.py`: pulls the given day's Jira worklogs (own only) into `worklog.tsv`. When an issue's Jira entries map 1:1 to an existing unposted local row, fills in `posted_at` (preventing double-registration); when there's no corresponding local row, appends a new row (importing history that exists only on the Jira side). When it can't map 1:1 (e.g. multiple rows for the same issue/date), defers to human review and doesn't touch anything.
  - Bug fix (2026-08-24): the local-row lookup only considered unposted rows, so an issue already synced (posted) was mistakenly treated as "not present locally," adding a duplicate row on every rerun. Fixed by broadening the lookup to include posted rows too, treating "all local rows already posted" as "already synced" and doing nothing.
- `bin/worklog/worklog_jira_validate.sh <from_date> <to_date>` (read-only) / `.py`: given a period, reports the consistency between `worklog.tsv` and Jira worklogs.
  - Any date+ticket with a ticket-level record (local or Jira) is reported as one row-pair, with `status` always `work`. Any date with zero records at all is classified via a separate day-level row (with `ticket`–`match` set to `-`) based on freee's `work_record` (`day_pattern`, `paid_holiday`, etc.): `holiday_public` if `day_pattern` is `prescribed_holiday`/`legal_holiday`, `holiday_private` if `paid_holiday` etc. is set, `absence` if `is_absence`, `not_posted_yet` if `clock_in_at` exists but there's no record, else `unknown`.
  - Decomposed into two axes — `local_state` (`posted`/`unposted`/`mixed`/`none`) and `match` (`match`/`mismatch`/`-`) — after feedback that a single combined status string mixed multiple concerns.
  - Flagged as a problem: `match=mismatch` (always) / `local_state=mixed` (always) / `local_state=posted` with nothing on the remote side / `local_state=unposted` with `match=match`.
  - Prints a fix suggestion (GUIDANCE) per problem row to stderr. ANSI-color-highlights problem rows on a tty; a `flag` column (`*`/`-`) on a non-tty.
- Measurement (2026-08-17–23): detected MMWAVE-787's double-posting risk, resolved via `worklog_jira_sync.sh 2026-08-17 --confirm`. Confirmed correct classification: the 18th as `holiday_private` (paid leave), the 22nd/23rd as `holiday_public` (company holidays), the 20th/21st as `not_posted_yet` (later recorded, resolving the flag).

#### New approach: per-ticket time aggregation via the JSON exchange format (decided, implemented, 2026-08-25)

Superseded the old approach following the shift away from using freee as a bounding frame (see the architecture section) and the "TSV deprecated in principle" policy.

##### Decided design

1. `worklog_session_turns_list.sh <date> <limit>` (read-only) emits the exchange-format JSON array (§11) for the given day's full session logs (SSoT => exchange format).
2. `worklog_session_infer.sh` (read-only, freee-independent) reads that JSON on stdin and aggregates runs of contiguous `(repo, ticket)` into per-ticket work-time candidates, emitted as a JSON array.
   - The day's outer bound is no longer freee's clock_in/clock_out — it's simply **the timestamp of the first turn through the last turn of that day's turns themselves**.
   - There's no longer a notion of a break (the freee punch data that used to source break info is no longer used). Only ticket changes form segment boundaries.
   - `note` defaults to the first non-empty `user` line within the segment (falling back to the fixed phrase "その他の雑多な作業"/"miscellaneous work" only when `ticket == GENERAL-451` and no such line is found). The actual conversation content becomes the note's draft directly.
3. A human directly edits the JSON (in VSCode, etc.) to reassign tickets, split segments, and fix notes, saving it as `bin/worklog/log/<date>.json`.
4. Validated via `worklog_lint.sh`, then handed off to the Jira-posting tools (see §12).

```bash
worklog_session_turns_list.sh 2026-08-24 none | worklog_session_infer.sh
```

##### Implementation

- `bin/worklog/worklog_session_turns_list.sh <date> <limit>` / `.py`: the source of the exchange format. Details in §11.
- `bin/worklog/worklog_session_infer.sh` / `.py`: aggregates the exchange format (stdin) => per-ticket segments (JSON). The freee lookups and `cwd => ticket` resolution the old version did on its own have both moved to the exchange-format generator (`worklog_session_turns_list.py`), leaving this script as pure JSON transformation (no more dependency on `repo_issue_from_cwd.sh`/`ticket_from_issue.sh` either).
- Measurement (2026-08-21 rerun, compared against the old approach): 85 turns split into 5 segments (vs. 6 under the old approach). The difference comes from two factors: (a) break-splitting no longer happens, and (b) `cwd => ticket` resolution reflects the *current* mapping state, so it can give a different answer than it did back on 2026-08-21 (concretely, the `56-carecom` worktree's ticket resolution had shifted from `MMWAVE-922` to `GENERAL-451`). (b) is a property of the exchange-format generation logic itself (re-resolving a past date can change depending on current config) rather than a regression introduced by this rewrite.
- Measurement (2026-08-24 data): 78 turns split into 3 segments, confirmed the notes reflect actual user utterances. However, in some cases the note's initial value ends up being the echo of a slash command like `/compact`, which isn't handled specially yet (room for improvement in a later phase).

### 11. Exchange format (JSON) schema (decided, implemented, 2026-08-25)

Produced by `worklog_session_turns_list.sh <date> <limit>`. Emits one record per "turn" (the unit bounded by `type:"system", subtype:"turn_duration"` events — one prompt : one response — primary information already computed per-turn by Claude Code itself) from the given day's session logs.

| Field | Content |
|---|---|
| `turn` | The turn_duration event's uuid (an identifier that uniquely points at this individual turn) |
| `timestamp` | The turn's completion time (ISO 8601, Asia/Tokyo) |
| `cwd` | The working directory at the time of the turn |
| `repo` | The repo display name resolved via the `cwd => repo => issue => ticket` chain (§9) (`none` if unresolvable) |
| `ticket` | Likewise, the ticket_key (`GENERAL-451` if unresolvable) |
| `user` | An array of the raw text the human actually typed during this turn. Injected text such as `<system-reminder>` is stripped. Images are excluded (text already present as text — e.g. text that came from reading an image — is kept as-is) |
| `agent` | An array of the top-level agent's utterances directed at the user (`thinking` blocks and ordinary tool_use/tool_result are not included). A sub-agent (Agent tool) call does not include the dialogue itself — only the facts `"calling subagent for <description>"` (at call time) and `"回答が来ました。<content>"`/"a reply came back. <content>" (when the result arrives) are recorded |

The `limit` argument (a non-negative integer, or `none`) sets the character-length cap for each `user`/`agent` line. Anything beyond it is truncated to `...(他N文字)`/`...(N more characters)` (the `calling subagent for`/`回答が来ました。` prefixes are not counted against the limit — only the body text is truncated).

Scope: filters every `turn_duration` event across all of `~/.claude/projects/**/*.jsonl` down to those falling within the target day's calendar date (00:00–24:00, Asia/Tokyo). Log files under `subagents/` are excluded (these are the sub-agent's own fork logs, not top-level records). Turns spanning multiple different session files are also merged and emitted as a single JSON array, sorted by timestamp ascending.

### 12. Persistence, and making Jira post/sync/validate exchange-format-aware (decided, implemented, 2026-08-25)

#### Problem

`worklog.tsv` used to serve as the single accumulator for the whole history. Retiring it leaves nowhere to persist "confirmed and posted" records (`worklog_session_infer.sh`'s segment JSON is only ever a transient output).

#### Decided design

- **`bin/worklog/log/<date>.json`** (e.g. `bin/worklog/log/2026-08-24.json`) is the new permanent store for confirmed/posted segments. Git-tracked. Takes over `worklog.tsv`'s "accumulate the whole history" role, split into one file per day.
- Posted status lives on each segment element as a `posted_at` field, right inside the file itself (the same idea as the old `posted_at` column in `worklog.tsv`).
- The overall workflow has been cut out into `instructions_to_ai_agent.en.md` as a procedure the AI Agent must follow (in particular, the "a human edits it" checkpoint must never be skipped)

#### Implementation

- `bin/worklog/worklog_lint.sh` / `.py` (new): successor to `worklog_tsv_validate.sh`. A read-only filter that reads the segment JSON array from stdin and checks required fields, `date`/`HH:MM` formats, `start < end`, `duration` consistency, same-`date` time-range overlaps, `date`/`start` ascending order, and `posted_at` format. Passes the array through to stdout unchanged if there are no problems.
- `bin/worklog/worklog_jira_post_batch.sh <file> [--dry-run] [--confirm]` / `.py`: rewritten to read/write `<file>` (the segment JSON) instead of `worklog.tsv`. POSTs elements whose `posted_at` is blank/absent, and writes `posted_at` back into the same file only for the ones that succeeded.
- `bin/worklog/worklog_jira_sync.sh <date> <file> [--dry-run] [--confirm]` / `.py`: added a `<file>` argument (dropped the fixed reference to `worklog.tsv`). The logic (1:1 matching per issue, and the "consider all local elements, not just unposted ones" bug fix from 2026-08-24) carries over unchanged. Creates `<file>` fresh if it doesn't exist.
- `bin/worklog/worklog_jira_validate.sh <from_date> <to_date>` / `.py`: signature unchanged. The "local" data source switched from `worklog.tsv` to `bin/worklog/log/<date>.json` (read per date in the range if present; treated as no local data for that date otherwise). freee is still used only to read that day's attendance classification (work/holiday/leave) — not as a bounding frame for work time — so this doesn't conflict with the architecture-section policy shift.
- Deleted `worklog.tsv` / `worklog_tsv.py` / `worklog_tsv_validate.py` / `.sh`, and `worklog_entry_start.sh`/`.py` / `worklog_entry_end.sh`/`.py` (see §7). Confirmed before deletion that every remaining reference was in the rewritten tools above.
- `worklog.tsv`'s existing data (2026-08-17–21, every row already had `posted_at` set — nothing unposted) was not migrated into `bin/worklog/log/`. Running `worklog_jira_validate.sh` over that period showed it matched Jira's records exactly with zero items needing review — Jira itself was already functioning as the record of truth for that period, so there was no real benefit to migrating it locally.

## Open items

- **Reversing the relationship with freee** (generating a "plausible-looking clock punch" from the exchange format): can't be mechanized deterministically, so this will be taken up once the rest of the worklog system is complete.
- **Quality of `worklog_session_infer.sh`'s default note text**: the echo of a slash command like `/compact` can end up as a segment's note default (see the "new approach" measurement notes in §10). Worth considering whether to strip more than just `<system-reminder>`.
- **The "what's next?" flow, candidate generation, and expanding what `worklog_lint.sh` checks**: `worklog_lint.sh` currently only does basic format checks. There's room to add checks later — e.g. whether `ticket` looks like a real Jira ticket key, or signs of duplicate posting.
- The candidate-generation logic surfaced by "what's next?". Fast forward resolution of `cwd => issue => ticket` is decided and implemented (§9). What remains open: which repo/issue to present as a candidate (JQL narrowing — e.g. assigned tickets or recently updated ones), and the fallback for sessions whose cwd doesn't map to a repository (termed a **stray session** — terminology decided 2026-08-21) or an unsynced issue.
- The `config.json` schema (what it should hold besides `MAX_TODO_COUNT`).
