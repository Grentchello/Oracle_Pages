---
title: Auto-Log Skill
date: 2026-09-27
type: skill
tags: [skill, workflow, journaling, auto-log]
---

# Auto-Log Skill

Enforce Grant's working method (see `wiki/_meta/method.md`): **every meaningful action is recorded in the wiki AND in today's daily note, then pushed to GitHub.**

This skill fires on every session — start, middle (after each task), and end. It's not a one-shot operation; it's a discipline.

## When This Skill Activates

Use this skill whenever:
- Starting a new session with Grant (always)
- Completing a task that should be remembered
- Ending a session
- Ingesting a source, creating/updating a wiki page, or finishing a non-trivial deliverable

If the user does something casual ("hi", "ok", a one-line question), skip it — the skill's own filtering rules decide what's "meaningful."

## What "Auto-Log" Means

**Four artifacts get written, in order. ALL FOUR are mandatory per session.**

1. **`wiki/daily/YYYY-MM-DD.md`** — the journal entry for today
2. **`wiki/log.md`** — append-only chronological action log
3. **Affected wiki pages** — new entities/concepts created or updated
4. **`wiki/_meta/method.md`** — update if workflow changed
5. **Git push** — commit and push to GitHub so the next session sees the changes

Daily note is the human layer; log.md is the machine layer; wiki pages are the compounding knowledge layer. Don't duplicate — each has a distinct purpose (see `_meta/method.md`).

**Daily note is mandatory per session, not optional.** Agents default to writing only `log.md` because it is quicker. That breaks the workflow because the daily note is what Grant actually reads. Before ending any session with code/wiki changes, **verify today's `wiki/daily/YYYY-MM-DD.md` exists and was updated this session**. If it wasn't, write the catch-up entry before saying "done." Skipping it for two days in a row is a class-A bug.

Quick session-end check:

```bash
ls -la /opt/data/hermes_work/wiki/daily/$(date -u +%Y-%m-%d).md
```

If missing or stale: write from the template below before claiming victory.

## Vault Location

The vault lives at:

```
/opt/data/hermes_work/      ← repo root, git-tracked
├── wiki/                   ← knowledge content (markdown)
├── mkdocs.yml              ← site generator config
├── .github/workflows/      ← GitHub Actions for auto-deploy
├── site/                   ← MkDocs build output (gitignored)
└── .venv/                  ← local Python venv for mkdocs (gitignored)
```

Synced to `https://github.com/Grentchello/oracle_Vault` via the PAT at `~/.config/hermes/.git_token` (Contents: Read+Write + workflow scope).

**The master dashboard** is rendered from `wiki/` by MkDocs Material and deployed to GitHub Pages. The dashboard lives in a **separate public repo** (`Grentchello/Oracle_Pages`) so the source vault can stay private. The GitHub Action in the public repo pulls from `oracle_Vault` (via the `ORACLE_VAULT_PAT` secret) and rebuilds on every push.

Live URL: **https://grentchello.github.io/Oracle_Pages/**

## Daily Note Format

Created automatically if missing. Filename is `daily/YYYY-MM-DD.md` where the date is **UTC** (Hermes container time). Schema:

```markdown
---
title: Daily — YYYY-MM-DD
date: YYYY-MM-DD
type: daily-journal
tags: [daily-journal]
---

# YYYY-MM-DD

> One-line summary

## Done
- [HH:MM] <task> — <outcome + link>

## Achievements
- <Milestone>

## Goals
- [ ] <Open item>
- [ ] <Next-session focus>

## Notes
- <Observations, decisions>

## Sessions
- [HH:MM-HH:MM] <source> — <summary>
```

**Carry-over:** at session start, if yesterday's `Goals` has unchecked items, prepend them to today's `Goals` with `(from YYYY-MM-DD)`.

## Workflow

### Step 1 — Detect / create today's daily note

```python
from datetime import datetime, timezone
import os

wiki = "/opt/data/hermes_work/wiki"
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
note_path = f"{wiki}/daily/{today}.md"

if not os.path.exists(note_path):
    create_daily_note(wiki, today)   # see template above
```

### Step 2 — Append to today's daily note

After each meaningful task:

```python
append_to_daily_note(note_path, section="Done", entry=line)
```

`append_to_daily_note` reads the file, finds the section, appends the line. If the section doesn't exist, insert it before `## Notes`.

### Step 3 — Append to log.md

For every discrete file change, append one entry:

```markdown
## [YYYY-MM-DD] <action> | <subject>
- <bullet: file path or change>
```

Actions: `ingest`, `update`, `query`, `lint`, `create`, `archive`, `delete`, `session-start`, `session-end`.

### Step 4 — Update wiki pages (if applicable)

If the task touches a wiki page: bump `updated`, add cross-links, update `index.md`, add provenance markers if synthesizing 3+ sources.

### Step 5 — Sync to GitHub

```bash
cd /opt/data/hermes_work
git add -A
git commit -m "<one-line summary of this commit>"
git push origin main
```

**Watch out for the sibling-repo trap:** if there's another git repo sitting at the same level (e.g. `/opt/data/hermes_work/oracle_pages/`), `git add -A` will pick it up as an embedded submodule (160000-mode file pointing at the sibling's tree) and bake that into history. Always keep sibling repo paths in `.gitignore` BEFORE the first `add -A`, or `git rm --cached <sibling>` immediately if it happens.

Verify the push succeeded before claiming "done." If push fails (token expired, network, conflict), surface the error to Grant — don't claim victory on a local commit that didn't reach origin.

## What Counts as "Meaningful"

| Action | Log it? | Where |
|---|---|---|
| Ingest a source | yes | daily + log + wiki pages |
| Create a wiki page | yes | daily + log + index |
| Update a wiki page | yes | daily + log + page (bump updated) |
| Run a script or task | yes (if milestone) | daily + log |
| Create a project folder | yes | daily + log |
| Ask/answer a query | only if filed | log + queries/ |
| Setup / config change | yes | daily + log |
| Casual chat ("hi", "ok") | no | — |
| Typo fix / formatting | no | — |
| Failed attempt before retry | log only (one line) | log |

## Session Bookends

**At session start:**

```bash
# 1. Read today's daily note (or yesterday's) to recall context
# 2. Read log.md last 30 lines
# 3. git pull origin main (in case another device edited)
cd /opt/data/hermes_work && git pull --ff-only origin main
```

**At session end:**

```bash
# 1. Ensure today's daily note is current
# 2. Commit any uncommitted wiki changes
# 3. Push to origin
# 4. Write session-end log entry
```

## Pitfalls

- **Don't write to daily notes that aren't today's** unless explicitly filling a gap. If you need to retro-log, do it once and timestamp it clearly.
- **Don't duplicate entries** — if it's already in log.md, don't put the same bullet in the daily note AND in the wiki page. Pick the most appropriate layer.
- **Don't push if commit fails** — investigate first; never claim success on a failed push.
- **Don't skip the daily note** because "nothing happened" — even "no user activity, idle" is a valid one-line entry. Silence is harder to debug than a quiet daily.
- **Don't write to log.md and daily/ in the same commit if they describe different things** — split for cleaner history.
- **The daily note is Grant's first read tomorrow** — write for him, not for the audit log.
- **If you discover you've been skipping daily notes for past sessions, write catch-up entries immediately.** Don't "fix it going forward" — fill the gap.

## Verification

After every auto-log write:

```bash
git -C /opt/data/hermes_work status
git -C /opt/data/hermes_work log --oneline -3
```

Both should show clean tree (or only intentional uncommitted) and the latest commit on `origin/main`. If they're behind, push.

## Related

- `wiki/_meta/method.md` — operating agreement
- `wiki/_meta/daily-journal.md` — daily note format spec
- `wiki/SCHEMA.md` — wiki conventions
