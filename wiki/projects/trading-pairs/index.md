---
title: Trading Pairs Bot
hide:
  - toc
---

# 📊 Trading Pairs Bot

> Multi-pair, multi-strategy paper trading on crypto CEX pairs. Inspired by Hummingbot's multi-strategy framework (see reference video below).

**Status:** v1 — running. Strategies: SUPER (trend), ROC (momentum), BB (volatility breakout), DIR (baseline).

## Live Dashboard
→ **[Trading Pairs Dashboard](pairs-dashboard.html)**

Refreshes every 30s. Mobile-friendly. Per-pair P&L, open positions, strategy leaderboard.

## How it works

**Pairs:** BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT, ARB/USDT

**Strategies (each runs on each pair independently):**

| Strategy | Signal | Position |
|---|---|---|
| **SUPER (trend)** | 20-EMA > 50-EMA | LONG, else flat |
| **ROC (momentum)** | Rate of Change > +2% over 15 candles | LONG, else flat |
| **BB (volatility)** | Price breaks upper Bollinger Band | LONG with stop at middle band |
| **DIR (directional)** | Baseline buy-and-hold per pair (long-only) | Always LONG |

**Position mechanics:**
- $100 paper per position
- TP: +1.5% (SUPER/DIR), +3% (ROC), +5% (BB)
- SL: -1% (SUPER/DIR), -2% (ROC), -3% (BB)
- Max 3 concurrent positions per pair (one per strategy)
- Total exposure capped at virtual $1500
- Time-stop: close after 4h if neither TP nor SL hit

**Tick cadence:** every 60s. Bot fetches latest prices + evaluates signals + manages open positions.

## Strategy leaderboard

Bot tracks each (strategy, pair) combo's realized P&L. Over time, this shows which strategies work for which pairs.

## Reference

Inspired by Hummingbot's UI: https://www.youtube.com/watch?v=z4_glUxQlWg (Agent Builders Cup — Condor + Hermes agent).

## Files

- `wiki/projects/trading-pairs/index.md` — this page
- `wiki/projects/trading-pairs/pairs-dashboard.html` — dashboard
- `bot/trading_pairs_bot.py` — bot logic (in vault, not yet)
- `wiki/trading-pairs/state.json` — bot state
- `wiki/trading-pairs/trades.json` — closed trades log
