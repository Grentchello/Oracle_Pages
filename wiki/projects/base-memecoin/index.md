---
title: Base Chain Memecoin Trading — v1.0
type: project
status: live
date: 2026-09-14
---

# Base Chain Memecoin Trading

**Project**: Autonomous paper-trading of Base chain memecoins (Coinbase L2). Started 2026-09-14 after Solana bot hit diminishing returns.

## Why Base?

- **Smaller market** = less competition for new launches
- **Coinbase integration** = native on-ramp, easier for retail
- **Different launchpads**: Clanker, Virtuals, Zora (not pump.fun)
- **Cheaper gas**: ~$0.10/swap vs Solana ~$0.001 but with less congestion
- **No GMGN needed** = DexScreener + DexPaprika are enough (both work from container)

## Strategy (v1.0 — conservative, learning)

### Entry Gates:
- **Liquidity**: $10k+ pool minimum
- **Volume**: $5k+ 24h
- **Age**: 2 min - 24h (no instant-pump entries)
- **No extreme pumps**: Reject if already +500% in 24h
- **No dumps**: Reject if -30% in 1h

### Decision Logic (simple scoring):
- +1: 24h vol > $50k
- +1: liquidity > $50k
- +1: buy pressure (buys > sells)
- +1: age < 60 min
- +1: micro-cap (<$500k mcap)
- +1: low FDV (<$2M)
- -2: sell pressure (sells > 2x buys)
- -2: dropping (chg24 < -50%)

**Score >= 2 = buy candidate**

### Position Management:
- Position size: **0.01 ETH** (~$25-30)
- Max concurrent: **1 position**
- Hard stop: **-20%**
- Max hold: **30 minutes**
- Daily loss cap: **-0.05 ETH**
- TP tiers: **+100% / +300% / +500%** (sell 25% / 50% / all)

### Slippage Simulation:
- Need pool >= 3x position size for safe exit
- If pool < 2x position = **GHOST EXIT** (record -100%, not paper profits)
- If pool < position = **90% slippage** applied

## Data Sources (all free, no API key):

| Source | Purpose | Endpoint |
|--------|---------|----------|
| **DexPaprika** | New pool discovery | `/networks/base/pools/search?sort=desc&order_by=created_at&limit=20` |
| **DexScreener** | Token profiles, boosts, pair data | `/token-profiles/latest/v1`, `/token-pairs/v1/base/{addr}` |

## Bot Files

- `bot/base_memecoin/base_bot.py` — main trading logic
- `bot/base_memecoin/runner.py` — 60s tick loop
- `bot/base_memecoin/data/state.json` — balance, positions, trades
- `bot/base_memecoin/logs/` — runner + bot logs

## Current Status

- Balance: 0.1 ETH
- Trades: 0 (waiting for first opportunity)
- Pairs scanned/tick: ~20
- Tick rate: every 60s
