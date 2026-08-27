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

## [2026-08-25] update | PAT upgraded with workflow scope
- Grant updated PAT scopes to include Workflows: Read+write
- Pushed .github/workflows/docs.yml successfully (commit 78f6801)
- Discovered GitHub Pages on private oracle_Vault is blocked (Free plan limitation)

## [2026-08-25] create | Oracle_Pages public repo for dashboard
- Grant created new public repo https://github.com/Grentchello/Oracle_Pages
- Cloned to /opt/data/hermes_work/oracle_pages
- Wrote GitHub Actions workflow that clones oracle_Vault (via ORACLE_VAULT_PAT secret) and builds MkDocs site
- Fixed three build failures: setup-python cache error, id-token permissions at workflow level, pip upgrade
- **Dashboard live at https://grentchello.github.io/Oracle_Pages/** — verified HTTP 200, title "oracle_Vault — Master Dashboard"
- Files: oracle_pages/.github/workflows/docs.yml, oracle_pages/README.md, mkdocs.yml (site_url updated)
- Commits: f827d9d, c60bac3, 6f5ee3c, e6813b7, c53f289 (all in Oracle_Pages)
- Latest commit in vault: 6d82894 (site_url → Oracle_Pages)

## [2026-08-25] create | First project: memecoin-trading
- Ultimate goal: autonomous memecoin trading bot
- Phase 1 foundation: live real prices, paper portfolio, no decisions yet
- Created wiki/projects/memecoin-trading/index.md with strategy candidates, infra decision table, status board
- Added project to mkdocs.yml nav
- Added project card to dashboard home (wiki/index.md) and projects/index.md
- Built bot/bot.py: fetches SOL price from DexScreener, top runners from pump.fun, persists state.json + watchlist.json + decisions.md
- Built wiki/trading/index.html + dashboard.css: phone-first, auto-refreshes every 30s, shows portfolio + holdings + watchlist + decisions
- Set up bot/runner.py (background loop, every 5 min) + Hermes cronjob "memecoin-bot-tick" (every 5 min) — redundant scheduling
- Verified: SOL price fetched live, 5-6 trending pump.fun tokens with DexScreener pairs, portfolio value computed, dashboard live at https://grentchello.github.io/Oracle_Pages/trading/
- Build #5 in Oracle_Pages succeeded
- Files: bot/bot.py, bot/runner.py, wiki/trading/index.html, wiki/trading/assets/dashboard.css, wiki/projects/memecoin-trading/index.md (revised), mkdocs.yml (added Trading nav)
- Vault commits: 823180e (dashboard), bot's auto-commits
- Oracle_Pages commit: 14aaa08 (rebuild trigger)

## [2026-08-25] update | Trading dashboard live
- Verified end-to-end: bot fetches live SOL price ($98.26), pushes to oracle_Vault, Pages rebuilds, dashboard loads
- Bot runner PID 43132 running, will tick every 5 min until container restart
- Hermes cronjob fc079fd07aa6 also scheduled (backup)

## [2026-08-25] update | Phase 2 trading live
- Built bot Phase 2: position manager, entry signals, exit rules, trade ledger
- Strategy: buy top-runners memecoins with $5k+ liq + $10k+ vol24h, 0.1 SOL per position, max 5
- Exits: take-profit +50%, stop-loss -30%, time-stop 24h, momentum-fade (24h flips neg AND ≥+20% profit), slot-pressure
- Dashboard updated: trade history section + win rate KPI + per-trade P&L breakdown
- Fixed earlier 404 (decisions.md → bundled into state.json as recent_decisions)
- Bot opened first positions: $unc, $BURNIE, $neet, $TripleT (4/5 slots used, 0.4 SOL deployed of 2.0)
- 0 closed trades yet — give it time
- Files: bot/bot.py (rewritten, 24KB), wiki/trading/index.html (rewritten, 13KB), wiki/trading/assets/dashboard.css (added trade styles)
- Paused cronjob (runner is sufficient)

## [2026-08-25] update | Strategy v2 — riskier, faster, learning
- Grant directive: aim for +20% in 24h, learn from every trade, take risks
- Tightened exits: TP -50%→+30% partial (sell half) + full TP at +60%, SL -30%→-20%, max-hold 24h→12h
- Added composite entry score: 24h change + recency bonus + turnover bonus + short-momentum boost (need ≥5.0 to enter)
- Added post-mortem analysis: every closed trade compares entry vs exit signals and diagnoses what changed
- Added Strategy Learning section: surfaces win/loss signal patterns once ≥3 wins AND ≥3 losses
- Added daily target tracking: +20% on 2 SOL paper = +0.4 SOL/day, dashboard has progress bar
- 4 open positions from earlier run will exit via new SL/time-stop rules; learning starts fresh
- Files: bot/bot.py (rewritten, 32KB), wiki/trading/index.html (daily bar, learning section, post-mortem in trade items), wiki/trading/assets/dashboard.css (new styles)
- Already-deployed HTML has 9 references to new features, daily_target_pct=20 in state.json

## [2026-08-25] update | Live price WebSocket via pumpportal.fun
- Grant directive: prices move fast, dashboard must reflect live
- Added WebSocket client to wiki/trading/index.html connecting to wss://pumpportal.fun/api/data
- Subscribes to subscribeTokenTrade for all watchlist mints + held positions
- Trade events update prices in real-time on the page (priceflash animation)
- Re-subscribes automatically when watchlist/positions change
- Auto-reconnects on disconnect
- No git/Pages involvement — pure browser→pumpportal.fun stream
- Bot still ticks every5 min for positions/PnL/stats; live stream just makes prices instant
- Files: wiki/trading/index.html (added ~120 lines WS code), wiki/trading/assets/dashboard.css (price-live animation)
- First closed trade under v2 strategy: $unc stopped out at -20.04%
  - Post-mortem: "HIGH-MOMENTUM BUT REVERSED — entered too late, smart money already exiting"
  - Real learning artifact for future strategy refinement

## [2026-08-26] update | Strategy v3 — LLM-decided, no hard exits
- v2 rules-based strategy failed: 1W/4L record, all losses were "buy the top" pattern
- Hard TP/SL/partial-TP all wrong for memecoins — they move too violently for mechanical rules
- Replaced rules with LLM-decided entries and exits (using MiniMax-M3 via Hermes gateway)
- Hard guardrails LLM can't override: 5 positions max, 0.1 SOL each, 72h max hold, 0.3 SOL daily loss cap, 0.1 SOL reserve
- Decision log persisted to wiki/trading/decision_log.json (last 100 entries) for review
- Dashboard has new "LLM Decision Log" section showing raw prompts + responses
- First LLM call: sold remaining $unc at -15.5% (better than -20% hard stop) with reasoning
  - "Entry signal failed: -15.5% from entry with -16% 24h and -13% in the last hour — momentum is bleeding out, not setting up for a bounce"
- Fixed dashboard "Loading…" bug: missing #updated element reference was killing the entire refresh function
  - Added setEl() helper for defensive element access
  - Verified with real Chromium browser using puppeteer-core + Playwright's bundled chromium
- Files: bot/bot.py (rewritten, 30KB), wiki/trading/index.html (decision log section, setEl helper)
- Killed old bot runner (proc_3b0b6243d8a0), started new one (proc_64d0aada1332) with v3 bot
## [2026-08-26] update | Tasks feature on master dashboard
- Grant asked to add a private todo list to the master dashboard, accessible via password
- Created wiki/tasks/tasks.json as the data source
- Created wiki/tasks/index.md — a self-contained HTML page with a password gate
- Password "oracle" (SHA-256 hash in the page). Client-side check, sessionStorage caching
- Added Tasks to MkDocs nav
- Added Tasks card to wiki/index.md master dashboard
- Created ~/.hermes/skills/productivity/tasks/SKILL.md so future task operations are consistent
- Verified with real Chromium browser: gate works, wrong password shows error, correct password shows the task
- Initial task: "Copy more house keys" (high priority)

## [2026-08-26] update | Vault password changed
- Grant set canonical vault password to `aW0^n7qZ^S`
- This password now protects the Tasks page and any future password-gated sections
- Updated tasks.json's PASSWORD_HASH in wiki/tasks/index.md
- Saved password + hash to Hermes memory so future sessions know it
- Updated tasks skill docs with the new password reference
- Old password "oracle" no longer works — verified via puppeteer

## [2026-08-27] update | Bot v5: liquidity-aware entries and exits
- Grant asked: prevent buying positions that can't be sold
- Found bug: DexScreener returns `liquidity.usd = null` for pump.fun tokens, so effective liquidity was always 0
- Fixed: bot now falls back to pump.fun `real_sol_reserves * sol_price` as liquidity proxy
- Pre-entry gate: skip buy if pool liquidity < 5x position size (need $50+ pool for $10 position)
- Exit-size cap: if position > 30% of pool, reduce sell fraction to avoid -90% slippage
- LLM prompt now shows `pool=$X, our share=Y%` for each holding + warns when share > 30%
- Dashboard Holdings panel shows colored liquidity badge (✓/⚠/✗) for each position
- Also added dedup-by-symbol check (LLM sometimes picks same mint twice)
- Files: bot/bot.py, wiki/trading/index.html, wiki/trading/assets/dashboard.css
- Verified: bot rejected $Aura (pool $0) and $PONY (pool $17); accepted $HOBBES (pool $910), $GREENPISTA (pool $3617)

## [2026-08-27] update | Bot v6: scalp-focused profit taking
- Grant observation: $Ai-Chan at +114% in 12 min — why hold longer? Should scalp
- Bug found: 8b take-profit was using `tokens` (fresh launches list) to look up held positions, but held tokens are NOT in fresh list — so 8b never fired
- Fix: use `held_prices` dict directly for held positions (correct lookup)
- Auto-TP tiers (non-negotiable, bot enforces):
  - +30% → sell 50%
  - +100% → sell 75%
  - +300% → sell 100%
- Stale-position exit: >60 min held AND pnl < +30% → auto-exit regardless of LLM
- LLM prompt rewritten with SCALPING DISCIPLINE section: aggressive profit-taking, fast exit on losers, skip weak entries
- Verified: $Topblast at +91.6% triggered TP +30% (half) successfully
- Verified: $CLAUDE at -50% auto-stopped
- Files: bot/bot.py

## [2026-08-27] update | Bot v6.1: stale-detection tightened + dashboard visible
- Grant observation: $Peter at 3.7h and +12% — stale, should have exited
- Bot v6 had stale at >60 min and pnl < +30% — too lenient for memecoins
- Tightened: stale auto-exit at >30 min AND pnl < +20%
- New soft stale warning in prompt: ⚠ STALE shows next to positions held >15 min with pnl < +10%
- LLM now sees staleness directly in the position line so it can act before the 30-min auto-exit
- Reset today's PnL counter to 0 (was -0.4562 SOL from yesterday's over-trading) — bot will resume trading
- Files: bot/bot.py
