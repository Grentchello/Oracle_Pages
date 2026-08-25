---
title: "Memecoin Trading Bot"
project_status: planning
project_created: 2026-08-25
project_owner: Grant
---

# Memecoin Trading Bot

> **Ultimate goal:** autonomous trading bot for memecoins.
> **Stage:** Phase 1 — foundation live (real prices, paper positions, dashboard).

## Summary

A bot that trades memecoins automatically. We start by:

- Fetching **real Solana prices** from DexScreener + pump.fun (no fabrication)
- Tracking a 2 SOL paper portfolio with virtual positions
- Showing live state on a phone dashboard
- Logging every bot decision with reasoning

When the foundation is solid, we'll add real signal detection and trade execution.

## Live dashboard

📱 **[grentchello.github.io/Oracle_Pages/trading/](https://grentchello.github.io/Oracle_Pages/trading/)**

The dashboard refreshes every 30 seconds. It shows:

- **SOL balance** — current 2 SOL holding + USD value
- **Total portfolio value** — including any open positions, with PnL
- **Holdings** — every token position with entry price, current price, 24h change
- **Trending on pump.fun** — top runners with market cap, liquidity, volume
- **Recent decisions** — the bot's last 10 thoughts/observations/actions

## Goals

- [x] **Phase 1: Foundation** (in progress, working)
  - [x] Fetch live SOL price from DexScreener
  - [x] Fetch trending pump.fun tokens
  - [x] Persist state.json + watchlist.json + decisions.md
  - [x] Phone dashboard at Oracle_Pages/trading/
  - [x] Bot tick runs every 5 min via cron + background runner
- [ ] **Phase 2: Signals** — detect momentum, volume spikes, near-graduation
- [ ] **Phase 3: Decisions** — bot actually buys/sells based on signals
- [ ] **Phase 4: Learning** — track outcomes, refine policy

## How it works

```
[Bot runner, every 5 min]
        ↓
1. Fetch SOL price from DexScreener (real, no auth)
2. Fetch top pump.fun runners (real, no auth)
3. Fetch DexScreener pairs for those mints
4. Compute portfolio value (positions × current prices)
5. Run decision policy (currently: observe)
6. Write state.json + watchlist.json + decisions.md
7. git commit + push → oracle_Vault
        ↓
[GitHub Actions cron, every 10 min]
        ↓
Pulls oracle_Vault → builds site → deploys to GitHub Pages
        ↓
[Your phone]
        ↓
Loads state.json + watchlist.json every 30s
```

## State files

| File | What it holds |
|---|---|
| `wiki/trading/state.json` | SOL balance, positions, trades, last prices |
| `wiki/trading/watchlist.json` | Trending tokens snapshot, refreshed each tick |
| `wiki/trading/decisions.md` | Append-only log of every bot decision |

## Strategy candidates

We haven't picked yet. Sketching the menu:

- **Sniper** — buy within seconds of liquidity appearing on a new pair
- **Momentum** — ride volume spikes / KOL mentions / trending tickers
- **Copy-trade** — mirror top on-chain wallets (e.g. via on-chain indexers)
- **Mean-reversion** — buy sharp dumps on previously hot tickers
- **Hybrid** — multiple signals feeding a single position-sizing rule

## Infrastructure decisions (open)

| Decision | Options | Status |
|---|---|---|
| Chain | Solana | chosen ✓ |
| Price source | DexScreener + pump.fun | live ✓ |
| Storage | git + JSON | live ✓ |
| Dashboard | GitHub Pages | live ✓ |
| Execution | cron + background runner | live ✓ |
| Bot logic | TBD (Phase 2) | not started |
| Live trading wallet | TBD (Phase 3+) | not started |

## Status

**Started:** 2026-08-25
**Last updated:** 2026-08-25 (live)

### In progress
- Phase 1 polish (dashboard refinements based on first user feedback)

### Done
- Project created
- Bot fetches real prices
- Dashboard live at Oracle_Pages/trading/
- Cron + background runner executing every 5 min

### Blocked
- None

## Notes

The dashboard auto-refreshes prices every 30s on your phone. The bot itself
only ticks every 5 min — that's the source of truth for positions and PnL.
If you want faster bot reactions, drop the interval to 1 min in `bot/runner.py`.

When the bot starts trading (Phase 3), every action lands in `decisions.md`
with a timestamp and reasoning — that's the "learning from every trade"
ledger.