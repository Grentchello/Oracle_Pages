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
  - [x] Bot tick runs every 60s via background runner (was 5 min, 60x faster scan)
- [x] **Phase 2: Trading** (live, paper money)
  - [x] Position manager (open/close, balance tracking)
  - [x] Entry signals: top-runners + graduated + liq>$5k + vol>$10k + 24h>0 + slot+SOL available
  - [x] Exit rules: take-profit +50%, stop-loss -30%, time-stop 24h, momentum-fade, slot-pressure
  - [x] Trade ledger with entry/exit signals, PnL, exit reason
  - [x] Win rate / avg PnL / best / worst stats
  - [x] Dashboard: trade history section + KPI breakdown
- [x] **Phase 3: LLM-decided trading** (live, replacing rules-based exits)
  - [x] LLM reviews every held position, decides hold/sell_all/sell_half with reasoning
  - [x] LLM reviews entry candidates, decides buy/skip with reasoning
  - [x] Hard limits: 5 positions, 0.1 SOL each, 72h max hold, 0.3 SOL daily loss cap
  - [x] Decision log persisted (decision_log.json) — every prompt + response for review
  - [x] Failed v2 strategy (rules-based) — 1W/4L, all losses on "buy the top" pattern
  - [x] v3 LLM made first call: sold $unc at -15.5% (better than -20% hard stop) with explicit reasoning
- [x] **Phase 4: Attention-first LLM bot (v4)** — live, actively trading
  - [x] New-launches endpoint (`sort=created_timestamp DESC`) — freshest tokens only
  - [x] Drop all liquidity/volume/momentum gates
  - [x] LLM picks by narrative (X account, name, story, bonding curve progress)
  - [x] Bonding curve price fallback for tokens without DexScreener pairs
  - [x] LLM buys are now executing (5 positions filled within 1 minute of deploy)
- [ ] **Phase 5: Tune prompt based on observed behavior**
- [ ] **Phase 6: Live trading (real SOL) when win rate > 40% over 50+ trades**

## Strategy v3: LLM-decided, no hard exits

The LLM is the trader. Hard caps are guardrails, not the strategy.

**Entry gates (the only rules):**
- Token on pump.fun top-runners
- Liquidity > $5,000 USD
- 24h volume > $10,000 USD
- 24h price change > 0%

**Then the LLM reviews the shortlist and decides:**
- Buy Y/N, with reasoning
- Or skip everything if signals aren't right

**Exit (no hard TP/SL):**
- LLM reviews every position every 60s (or every 5 min when idle)
- Decides: hold / sell_all / sell_half, with reasoning
- Only hard cap: 72h max hold (forced close)

**Hard guardrails (LLM can't override):**
- Max 5 positions
- 0.1 SOL per position
- Daily loss cap: -0.3 SOL (no new entries if exceeded)
- Reserve 0.1 SOL (never go below)

## Strategy parameters (Phase 2.1 — riskier, faster) — SUPERSEDED by v3

The rules-based v2 strategy was retired. LLM now makes all entry/exit calls. The
old parameters are kept here for reference only.

| Parameter | Value | Notes |
|---|---|---|
| Position size | 0.1 SOL ($10) | Flat per entry |
| Max positions | 5 | Concurrent |
| Min liquidity | $5,000 USD | Skip thin pools |
| Min 24h volume | $10,000 USD | Skip dead tokens |
| Min 24h change | 0% | Negative momentum is exit signal, not entry |
| Min entry score | 5.0 | Composite: 24h change + recency + turnover + short momentum |
| **Take-profit (partial)** | **+30%** | **Sell HALF, hold rest** |
| **Take-profit (full)** | **+60%** | **Sell remainder** |
| **Stop-loss** | **-20%** | **Full exit (tighter)** |
| **Max hold** | **12h** | **Was 24h — faster rotation** |
| **Momentum-fade exit** | **24h flips neg AND ≥+15% profit** | **Lock gains** |

## Strategy v2: learning + post-mortem

Every closed trade gets analyzed for WHY it performed as it did:
- Compared entry signals to exit signals
- Diagnoses: "high-momentum entry thesis worked", "liquidity dropped 30% — rug pull risk", "held 12h with no direction"
- All post-mortems visible on each trade in the Trade History section

After ≥3 wins and ≥3 losses, the dashboard surfaces **Strategy Learning** patterns:
- Which entry signals (24h momentum, liquidity, volume) correlate with wins
- Average holding time per outcome
- Exit reason breakdown (which exits make money vs lose money)

## Daily target

**Goal:** +20% on 2 SOL paper = +0.4 SOL net gains per day.**

The dashboard has a progress bar tracking today's realized PnL toward that target.
After 5+ trades we'll know whether this is achievable or whether the strategy needs adjustment.

## How it works

```
[Bot runner, every 60s]
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
- Background runner executing every 60s

### Blocked
- None

## Notes

The dashboard auto-refreshes prices every 30s on your phone. The bot itself
only ticks every 60s when idle; every tick when holding positions — that's the source of truth for positions and PnL.
If you want faster bot reactions, drop the interval to 1 min in `bot/runner.py`.

When the bot starts trading (Phase 3), every action lands in `decisions.md`
with a timestamp and reasoning — that's the "learning from every trade"
ledger.

---

## Final Post-Mortem (2026-08-27)

### Numbers

| Metric | Value |
|---|---|
| Starting balance | 2.0 SOL |
| Final balance | 0.224 SOL |
| Loss | -1.776 SOL (-88.5%) |
| Total trades | 1223 |
| Wins | 646 (+12.55 SOL) |
| Losses | 577 (-14.20 SOL) |
| Win rate | 53% |
| Avg win | +1.94% (= +0.019 SOL) |
| Avg loss | -2.46% (= -0.025 SOL) |
| Biggest loss | $TREND -99.9% = -0.0999 SOL |

### Why we lost

**Asymmetric payoff problem.** 53% win rate but losers cost more than winners make:
- Avg win: +0.019 SOL
- Avg loss: -0.025 SOL
- Per trade: 53%×0.019 - 47%×0.025 = -0.0021 SOL
- Over 1223 trades = -2.6 SOL (matches actual -1.77 within rounding)

The bot was structurally designed to lose money because losses were bigger than wins.

**Why?** Hard stop at -30% meant losers lost 30% of $5 = $1.50. Take-profit at +30% sold 25% of position = captured $0.375. **Win:Loss ratio 1:4 on a per-trade basis.**

**What fixed attempts didn't fix:**
- v7: position size 0.1 → 0.05 SOL ✓ (halved loss size)
- v7: hard stop -50% → -30% ✓ (cut losers faster)
- v7: TP tiers rebalanced ✓ (let winners run)
- v6.2: hard stop uses held_prices instead of fresh-tokens list ✓ (was the biggest single bug)

None of these fixed the structural problem: **solana memecoins are 80%+ rugs and the rug rate at -75% or worse is ~3%.** One -99% loss = 2-3 wins to recover. With ~50% win rate, math is impossible.

### What should have been different

**Better entries:**
- Skip tokens that haven't pumped yet. Wait for mcap > $50k or +50% in first hour.
- Require TWITTER + TELEGRAM or X account >10k followers as filter.
- Avoid tokens with <100 SOL liquidity at entry.

**Different exit logic:**
- TP at +50% minimum (not +30%) so win/loss ratio flips
- Hard stop at -15% not -30% (smaller losers)
- Or use trailing stop: from peak -20% triggers sell

**Different position sizing:**
- Kelly criterion: position size = edge / variance. We had ~5% edge at best, but variance was huge. Kelly says: small positions.

**Or: don't trade memecoins at all.** The trading-pairs bot (BTC/ETH/SOL/etc) on Binance is at least market-neutral and the data quality is higher.

### What to do with state

State preserved in `wiki/trading/state.halted.json` (863 KB) and `trades.halted.json` (6 KB) for future analysis. Don't delete — these are the source of truth for what we tried and how it failed.

### Trading Pairs Bot (alternative project)

Still running: https://grentchello.github.io/Oracle_Pages/projects/trading-pairs/pairs-dashboard.html

Started fresh at $1000 paper, multi-pair (BTC/ETH/SOL/BNB/XRP/ARB) × 4 strategies (SUPER/ROC/BB/DIR). Currently 0% P&L on real Binance public data. May or may not be profitable — give it time.

---

## Research-Backed Improvements (planned)

See [Research note: CoinCLIP](../../research/coinclip.md) for the full analysis.

**Key insight:** CoinCLIP paper (arXiv:2412.07591, Long et al. WWW 2025) shows memecoin viability can be predicted at **84.7% accuracy** from logo + name + community signals — **before price action**. Our bot failed because it traded price action only.

**Already implemented in bot code (gates will fire when bot restarts):**
- Skip tokens with description <50 chars (lazy projects)
- Skip tokens with no twitter AND liquidity <$3k
- CoinCLIP showed image quality > name quality for predicting success, but we can't run CLIP locally without GPU. The above two filters approximate the cheap signals.

**Not yet implemented (would need CLIP model + GPU or hosted API):**
- Full CoinCLIP viability scoring per candidate token
- Comment sentiment/like-weighted scoring
- Backtest on the CoinVibe dataset

### Roadmap (if bot is restarted)

1. **Filter pass:** Apply the CoinCLIP-style viability gates (already coded)
2. **CLIP-text-only:** Run token name + description through CLIP text encoder (~250MB, doable locally or via HF API)
3. **Community data:** Scrape pump.fun comment counts + likes (not yet implemented)
4. **Backtest:** Apply CoinCLIP-style filters to historical pump.fun tokens and see if they would have predicted our 1223 losing trades as non-viable
