---
title: "Memecoin Trading Bot"
project_status: planning
project_created: 2026-08-25
project_owner: Grant
---

# Memecoin Trading Bot

> **Ultimate goal:** autonomous trading bot for memecoins.
> **Stage:** ground zero — research and design phase.

## Summary

Build a bot that trades memecoins automatically. The bot should:

- Detect new token launches or momentum signals
- Decide whether to enter a position
- Manage entries, exits, and risk
- Run unattended once configured

We start from zero — no infrastructure, no live trading, no committed
strategy. Every decision below is open.

## Goals

- [ ] Research existing memecoin trading approaches and what's worked/died in 2026
- [ ] Decide on exchange(s) — CEX (Binance, Bybit) vs DEX (Solana, Base, ETH)
- [ ] Pick a strategy class — sniper, momentum, copy-trade, hybrid
- [ ] Define risk parameters — max position size, daily loss limit, stop rules
- [ ] Build a paper-trading version that runs against live data without real capital
- [ ] Track performance — log every signal, decision, trade, PnL
- [ ] Move to small live capital once paper trading shows edge
- [ ] Document every lesson as it happens

## Strategy candidates

We haven't picked yet. Sketching the menu:

- **Sniper** — buy within seconds of liquidity appearing on a new pair
- **Momentum** — ride volume spikes / KOL mentions / trending tickers
- **Copy-trade** — mirror top on-chain wallets (e.g. via on-chain indexers)
- **Mean-reversion** — buy sharp dumps on previously hot tickers
- **Hybrid** — multiple signals feeding a single position-sizing rule

## Infrastructure decisions (open)

| Decision | Options | Notes |
|---|---|---|
| Chain | Solana / Base / ETH L2 | Solana is the memecoin home right now |
| Exchange API | Jupiter (SOL) / 0x / Uniswap router | DEX-native; avoids CEX KYC |
| Language | Python / Rust / TypeScript | Python fastest to prototype |
| Hosting | This VPS / a separate cheap box / cloud | needs <50ms to Solana RPC |
| Data sources | Birdeye / DexScreener / on-chain indexer | price + liquidity + holder data |
| Wallet management | Single hot wallet vs per-trade ephemeral | security vs ops complexity |

## Status

**Started:** 2026-08-25
**Last updated:** 2026-08-25

### In progress
- Researching exchange/wallet options

### Done
- Project created

### Blocked
- None

## Notes

Open floor for whatever I find while researching. Trade journal will live in a
subfolder once we have a paper-trading run going — that's where the actual
edge gets measured.

## Links

- Source repo: TBD
- Related wiki pages: TBD
- External resources: TBD