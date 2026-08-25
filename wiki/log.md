# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-08-25] create | Wiki initialized
- Vault: https://github.com/Grentchello/oracle_Vault
- Domain: open-ended (Grant's personal KB)
- Hermes Agent wired up with GitHub PAT (Contents: Read+Write) for sync
- Structure created: SCHEMA.md, index.md, log.md, raw/, entities/, concepts/, comparisons/, queries/, _meta/

## [2026-08-25] session-start | Vault bootstrap + auto-log skill
- Moved wiki from /opt/data/home/wiki to /opt/data/hermes_work/wiki (Grant's layout rule)
- Wrote `_meta/method.md` and `_meta/daily-journal.md` documenting the auto-log workflow
- Created `daily/` folder and today's daily note `daily/2026-08-25.md`
- Updated SCHEMA.md, index.md to reference the daily-journal layer
- Created `auto-log` skill — enforces wiki logging + daily note on every session
- Files: _meta/method.md, _meta/daily-journal.md, SCHEMA.md, index.md, daily/2026-08-25.md