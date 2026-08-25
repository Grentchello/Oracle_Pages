---
title: Daily Journal — Format and Rotation
created: 2026-08-25
updated: 2026-08-25
type: concept
tags: [meta, daily-journal, workflow]
sources: []
---

# Daily Journal

> One markdown file per day. The journal layer of the wiki.
> Created automatically by the `auto-log` skill at session start.
> Read first thing every session to recall context.

## Location

```
wiki/daily/YYYY-MM-DD.md
```

Filenames are date-only — sortable, no leading zeros (`2026-8-25` is fine, `2026-08-25` is canonical).

## File format

```markdown
---
title: Daily — YYYY-MM-DD
date: YYYY-MM-DD
type: daily-journal
tags: [daily-journal]
---

# YYYY-MM-DD

> One-line summary of the day.

## Done
- [HH:MM] <task or action> — <outcome, link to wiki page or commit>
- [HH:MM] <task> — <outcome>

## Achievements
- <What's now possible / a milestone reached>

## Goals
- [ ] <Open item, possibly carried over from yesterday>
- [ ] <Next-session focus>

## Notes
- <Observations, surprises, decisions, links to remember>

## Sessions
- [HH:MM-HH:MM] <source> — <summary>
```

## When sections appear

- `Done`, `Goals`, `Notes`, `Sessions` — always present, even if empty
- `Achievements` — only when something meaningful happened (skip on quiet days)

## Rotation

When `daily/` has more than 90 entries, roll the oldest month into
`daily/_archive/YYYY-MM/`. Don't lose history — just keep the active
folder scannable.

## Stale daily notes

A daily note from an unfinished previous day is a focus artifact, not
garbage. At session start:

1. If yesterday's note has unchecked goals, surface them.
2. Append them to today's `Goals` section as carry-overs.
3. Mark them with `(from YYYY-MM-DD)` so the lineage is clear.

## See also

- [[method]] — overall workflow rules
- [[SCHEMA]] — frontmatter spec