---
title: Method of Working — Hermes + Grant
created: 2026-08-25
updated: 2026-08-25
type: concept
tags: [meta, workflow, method, daily-journal, hermes-work]
sources: []
---

# Method of Working — Hermes + Grant

> The operating agreement between Grant and [[oracle_Vault|the vault]]'s Hermes agent.
> Updated when the workflow changes. Triggers on every session.

## The rule

**Every meaningful action Hermes takes is recorded in the wiki, and a daily note
captures what was done, achieved, and what's next.** The vault is the single
source of truth for our work together.

## Where things live

All work sits under `/opt/data/hermes_work/`:

```
/opt/data/hermes_work/
├── wiki/         ← knowledge vault (this repo)
└── <projects>/   ← per-project subfolders, one per initiative
```

## Layers of recording

There are four, each with a distinct purpose. Don't conflate them.

### 1. Wiki pages (`entities/`, `concepts/`, `comparisons/`, `queries/`)
Compiled, cross-linked knowledge. The compounding layer.
- Created when an entity/concept meets the page threshold (see [[SCHEMA]])
- Updated when new sources or insights land
- Indexed in `index.md`

### 2. `log.md` — chronological action log
Append-only ledger of every discrete wiki action.
- Format: `## [YYYY-MM-DD] action | subject`
- One line per file change in batch ingests
- Rotates when it hits 500 entries

### 3. Daily notes (`daily/YYYY-MM-DD.md`)
**The journal.** One file per day. Captures:
- **Done** — what got accomplished
- **Achievements** — what's now possible that wasn't before
- **Goals** — what's still open / next session's focus
- **Notes** — loose observations, surprises, decisions

Daily notes are human-readable, less formal than wiki pages, and are the
first thing to read at session start to recall context.

### 4. `log.md` session markers
Each chat session with Hermes gets bracketed entries in `log.md` so the
timeline is easy to scan:

```
## [2026-08-25] session-start | Grant asked X
## [2026-08-25] ingest | Source Y → entities/z.md
## [2026-08-25] session-end | Outcome: Z
```

## Workflow per session

1. **Open** — Hermes reads `log.md` (last 30 lines) + today's daily note (or yesterday's if none) to recall context.
2. **Work** — Grant directs; Hermes executes and **records in real time**, not at the end.
3. **Close** — Hermes ensures today's daily note is current, syncs to GitHub, and writes the session summary into `log.md`.

## Triggers for what gets recorded

| Action | Records to | Daily note mention? |
|---|---|---|
| Ingest a source | `raw/` + affected wiki pages + `log.md` | yes (one-line summary) |
| Update a wiki page | the page + `log.md` | yes (one-line summary) |
| Create a project folder | `log.md` | yes (substantial — what the project is) |
| Run a task outside the wiki | `log.md` only | yes if it's a milestone |
| Ask/answer a query | if valuable, `queries/` + `log.md` | only if filed |

Rule of thumb: **if Grant would want to remember it later, it gets a daily note mention.**

## What does NOT get recorded

- Trivial back-and-forth ("hi", "ok", small clarifications)
- Pure formatting / typo fixes
- Internal tool noise

## See also

- [[SCHEMA]] — wiki conventions and frontmatter
- [[index]] — content catalog
- [[daily-journal]] — daily note format and rotation policy
- [[oracle_Vault]] — repo metadata
## Communication style

**Default mode: caveman full.** Every response compressed: drop articles (a/an/the), filler (just/really/basically), pleasantries (sure/certainly/of course), hedging. Fragments OK. Short synonyms (fix not "implement a solution for"). No tool-call narration, no decorative tables/emoji unless asked. Tool calls fire direct, no preamble.

Setup at session start:
- Config: `~/.config/caveman/config.json` = `{"defaultMode": "full"}`
- Env: `CAVEMAN_DEFAULT_MODE=full` in `~/.bashrc`

Deactivate: say "stop caveman" or "normal mode".

Keep technical terms, code, commands, commit types, exact error strings verbatim.
