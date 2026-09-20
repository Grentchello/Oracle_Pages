---
title: Copy-Trading Wallet Discovery
type: project
status: live
date: 2026-09-20
---

# 🔍 Copy-Trading Wallet Discovery

**Goal**: Find Solana wallets that are profitable to copy-trade, while filtering out anti-copier wash strategies and wealth-transfer bridges.

**Last scan**: 2026-09-20T01:15:46Z
**Chain**: Solana
**Window**: 30-day stats (GMGN doesn't support 60d natively)

## 📊 Current Top 17 Traders (sorted by 60-day proxy score)

**Scoring formula**: `realized_profit × (win_rate / 100) × log(unique_tokens + 1) − wash_score × 10`

| # | Wallet | Win Rate | PnL 30d (SOL) | Tokens | Score | Wash |
|---|--------|----------|---------------|--------|-------|------|
| 1 | [`7JVQMwRj...`](https://solscan.io/account/7JVQMwRj82STgsG57spj6vpE6XY3RqG8B64PczVc7jJr) | 48.7% | 56,003 | 2529 | 213,654 | 3 |
| 2 | [`D9UiteKB...`](https://solscan.io/account/D9UiteKBjbVp8UYGRSKi4fJRsXYp8Csk7zcrnaCvq6LS) | 53.3% | 51,809 | 2056 | 210,529 | 0 |
| 3 | [`tBVFi3uh...`](https://solscan.io/account/tBVFi3uhRxDtn4C5Sxy7D6yUQ2qUfp2qkjcoL6ttmFt) | 39.9% | 34,238 | 2590 | 107,212 | 3 |
| 4 | [`55msLm12...`](https://solscan.io/account/55msLm128tQdXLXCXLxd756H9SaCo7wPpdetEioe7D8d) | 35.2% | 31,667 | 2484 | 87,253 | 0 |
| 5 | [`AzWnNS9i...`](https://solscan.io/account/AzWnNS9isJR9HZ6WAEAUwqVMu5SAwHsPNmrmEVCroyMS) | 48.9% | 13,037 | 1972 | 48,341 | 0 |
| 6 | [`7fnq9wNj...`](https://solscan.io/account/7fnq9wNj5WoMxasNcWNWS88peQjdWb1m5k8qS7grxGt2) | 30.4% | 24,360 | 505 | 46,132 | 0 |
| 7 | [`Gainsdr1...`](https://solscan.io/account/Gainsdr1kr3bEm5v3NV782v5PgrZD5QHhhcV2zRsYetS) | 60.2% | 12,917 | 342 | 45,389 | 0 |
| 8 | [`9tY7u1Hg...`](https://solscan.io/account/9tY7u1HgEt2RDcxym3RJ9sfvT3aZStiiUwXd44X9RUr8) | 30.6% | 16,403 | 2119 | 38,376 | 2 |
| 9 | [`CvRhs2dG...`](https://solscan.io/account/CvRhs2dG5WakRPmAAEzU7q5dExJQabUBqhivsRvKe2Cz) | 36.6% | 12,386 | 824 | 30,421 | 0 |
| 10 | [`4AufoJdJ...`](https://solscan.io/account/4AufoJdJBgMfev5feAgFiXwmsQRxZgtCaT1zVdWV7dhB) | 41.1% | 7,105 | 1153 | 20,573 | 0 |
| 11 | [`4gzfeWoB...`](https://solscan.io/account/4gzfeWoBQmV7ednrfcRh26AqmTrxm7MDpR1kH8x3wcNn) | 41.4% | 6,714 | 1155 | 19,588 | 0 |
| 12 | [`6vHTn67M...`](https://solscan.io/account/6vHTn67M8X5wDFB2eaeHu1WL8R6a7Xk6WfiBe6u5vkWb) | 42.1% | 6,398 | 1159 | 19,017 | 0 |
| 13 | [`9shBHjvi...`](https://solscan.io/account/9shBHjviUuynNdSS7Rks6jzqBYqB4aoGkAVU1gJpBkqt) | 61.4% | 3,464 | 1309 | 15,276 | 0 |
| 14 | [`CXRvRk6C...`](https://solscan.io/account/CXRvRk6Ci8fu4pqNd4fxDwHjzfkAzXm1dqFzwbuodfqh) | 32.5% | 6,450 | 174 | 10,791 | 3 |
| 15 | [`7rAZENrv...`](https://solscan.io/account/7rAZENrvWj9N3quFKjB1m4Qg58gbvzc2S5Smx3Xs6nE8) | 49.2% | 2,730 | 1731 | 10,017 | 0 |
| 16 | [`A4Jf7yqb...`](https://solscan.io/account/A4Jf7yqbdiKQHiRx6pHM7eJT7BDDdMvAHPhrQRKW3ZGe) | 40.6% | 2,949 | 199 | 6,337 | 0 |
| 17 | [`Eu1KU118...`](https://solscan.io/account/Eu1KU118rGQEAMnV5uXojfdx6nhozSgNr4Fhxi2suxHB) | 41.8% | 829 | 255 | 1,923 | 0 |


## 🎯 Anti-Copier + Anti-Bridge Filters Applied

### GMGN Tag Filters (auto-exclude)
- ❌ `wash_trader` — Explicitly flagged wash strategies
- ❌ `bundler` — Multi-buy same-block (pump coordination)
- ❌ `snipe_bot` — MEV snipers (unfair edge)
- ❌ `bot` — General bot behavior

### Wash Pattern Detectors (score-based, exclude if >=5)
1. **Instant roundtrips** — Buy + sell within 5s on same token (+1 each)
2. **High sell/buy ratio** — Sells >85% of buys = dumping on copiers (+3)
3. **Bundled buys** — Same-block multiple buys = coordinated (+2 each)
4. **Small-buy-large-sell trap** — Avg buy <$20, any sell >$500 (+2)
5. **High frequency trader** ⚡ — Avg interval <2 min between trades = bot/sniper (+4)
6. **Same-token repeat flipper** 🔁 — 3+ side flips on same token in 5 min (+3 per token)
7. **Multi-token per tx** 🌉 — 3+ tokens moved in single tx = bridge/aggregator (+5 if ≥5 txs, +2 if ≥2)
8. **Atomic pair trades** 💱 — Buy A + sell B in same tx = atomic swap, not trading (+4 if ≥10, +2 if ≥3)

### Why these matter
- **Wealth transfer / bridges**: Move assets between tokens as portfolio rebalancing, not directional bets. Huge volume but no real trading signal.
- **Atomic swaps**: Swap token A → B in 1 transaction. Not "buying B because it's bullish" — just portfolio rebalance.
- **Multi-token per tx**: Real traders do 1 token per tx. Bridges/exchanges do many.

## ⚠️ Caveats

- **GMGN only provides 30-day stats** — we use score weighting as a 60d proxy
- **Wallets with `top_renamed` / `top_followed` tags** may be baiting copiers — review before following
- **High PnL + low win rate** suggests volume-based strategy (risky to copy)
- **High win rate + low PnL** suggests small positions (less interesting)

## 📁 Files

- **Top traders data**: `/opt/data/hermes_work/bot/copy_trading/top_traders_60d.json`
- **Discovery script**: `/opt/data/hermes_work/bot/copy_trading/wallet_discovery.py`
- **Cache**: `/opt/data/hermes_work/bot/copy_trading/cache/`

## 🛠️ How to Run Discovery Again

```bash
cd /opt/data/hermes_work/bot
python copy_trading/wallet_discovery.py
```

Runs in ~2 min (fetches stats for each wallet one at a time due to GMGN CLI limits).
