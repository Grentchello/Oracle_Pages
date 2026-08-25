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

## [2026-08-25] create | MkDocs master dashboard
- Restructured git repo: /opt/data/hermes_work/ is now the root, wiki/ is subfolder
- Set up MkDocs Material with phone-friendly theme (dark/light, custom CSS, instant nav)
- Created master dashboard at wiki/index.md with project cards + recent activity
- Created projects/ folder with index.md + _template/ for sub-dashboards
- Created indexes for daily/, entities/, concepts/, comparisons/, queries/
- Wrote GitHub Actions workflow for auto-deploy to GitHub Pages
- Verified MkDocs build locally — all pages return 200, mobile viewport OK
- Pushed restructure (commits be628b9, 3ce4dff)
- Files: mkdocs.yml, wiki/index.md, wiki/projects/, wiki/daily/index.md, wiki/entities/index.md, wiki/concepts/index.md, wiki/comparisons/index.md, wiki/queries/index.md, wiki/assets/extra.css, .github/workflows/docs.yml

## [2026-08-25] pending | Workflow file upload
- .github/workflows/docs.yml ready locally but unable to push (PAT lacks `workflow` scope)
- Waiting for Grant to regenerate PAT with `workflow` scope OR opt for manual paste via GitHub UI
- Once landed: enable Pages (Settings → Pages → Source: GitHub Actions) → site goes live at https://grentchello.github.io/oracle_Vault/