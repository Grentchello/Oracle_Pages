---
title: Copy-Trading Wallet Discovery
type: project
status: live
date: 2026-09-20
---

# 🔍 Copy-Trading Wallet Discovery

**Goal**: Find Solana wallets that are profitable to copy-trade, while filtering out anti-copier wash strategies.

**Last scan**: 2026-09-20T00:45:29Z
**Chain**: Solana
**Window**: 30-day stats (GMGN doesn't support 60d natively)

## 📊 Current Top 22 Traders (sorted by 60-day proxy score)

**Scoring formula**: `realized_profit × (win_rate / 100) × log(unique_tokens + 1) − wash_score × 10`

| # | Wallet | Win Rate | PnL 30d (SOL) | Tokens | Score | Wash |
|---|--------|----------|---------------|--------|-------|------|
| 1 | [`8X5pJ2J3...`](https://solscan.io/account/8X5pJ2J34ShQDZ1MYMEuKg7UpqFgbsymENB2sbxQMDsE) | 49.0% | 132,147 | 1961 | 490,814 | 0 |
| 2 | [`7JVQMwRj...`](https://solscan.io/account/7JVQMwRj82STgsG57spj6vpE6XY3RqG8B64PczVc7jJr) | 48.8% | 55,952 | 2527 | 213,742 | 0 |
| 3 | [`4A2GsbyN...`](https://solscan.io/account/4A2GsbyNfQdqvf1Upz8GTXf6f3j5tcx8qko5yMbiFD8D) | 35.0% | 88,839 | 949 | 213,377 | 0 |
| 4 | [`D9UiteKB...`](https://solscan.io/account/D9UiteKBjbVp8UYGRSKi4fJRsXYp8Csk7zcrnaCvq6LS) | 53.3% | 51,821 | 2056 | 210,792 | 0 |
| 5 | [`H3rUiKEF...`](https://solscan.io/account/H3rUiKEFPnTM6CHCmJqKt4Nd1xeFATK9aUmU4sbD5za7) | 61.2% | 9,324 | 1238 | 40,625 | 3 |
| 6 | [`5h857Rqm...`](https://solscan.io/account/5h857RqmgcSjf2yz6E9Jh2zga5RaYTKzm1yK4uSnKD7n) | 47.9% | 9,370 | 1069 | 31,287 | 0 |
| 7 | [`4JSJp3yu...`](https://solscan.io/account/4JSJp3yuLRFwboNw2G5k2vJkonYvPB71SjRcJpvuRMJ3) | 54.3% | 7,639 | 958 | 28,473 | 0 |
| 8 | [`W1Dofh35...`](https://solscan.io/account/W1Dofh35sqLnqcXLPYqrNfGBeVza4YVfQUyzRcUa1yy) | 57.1% | 7,516 | 138 | 21,193 | 0 |
| 9 | [`EbW5XhDa...`](https://solscan.io/account/EbW5XhDaVUNy86cFH68BMydpp9ts3RoR4ZgHUrGHV5z2) | 53.4% | 4,290 | 1193 | 16,242 | 0 |
| 10 | [`GEtseN2g...`](https://solscan.io/account/GEtseN2g1twE19mGsBMXq2mVBh2zMW4E5m9Zq8iLQHQr) | 38.8% | 6,398 | 378 | 14,757 | 0 |
| 11 | [`9NXNywh7...`](https://solscan.io/account/9NXNywh7n8d8ihgUY2FcJn9hEPwXkYCdLyBdbFiDm4rs) | 59.0% | 3,171 | 1330 | 13,454 | 0 |
| 12 | [`3Ycnj9Rq...`](https://solscan.io/account/3Ycnj9RqQW3eEhhaxFPzbeDSzpeKRFytT9KHJLtd3RZm) | 48.0% | 3,425 | 2045 | 12,539 | 0 |
| 13 | [`F2ysh3Jm...`](https://solscan.io/account/F2ysh3Jm2m7rCBHjYDcnvt2GMX74nqDtzgjcRWfX111) | 37.5% | 4,350 | 669 | 10,603 | 0 |
| 14 | [`7rAZENrv...`](https://solscan.io/account/7rAZENrvWj9N3quFKjB1m4Qg58gbvzc2S5Smx3Xs6nE8) | 49.2% | 2,676 | 1730 | 9,814 | 0 |
| 15 | [`HhzJfEaP...`](https://solscan.io/account/HhzJfEaP1QNNZBLW3PvQ3c62J4Wc5mG3w43LaF2B67Jo) | 36.7% | 2,762 | 156 | 5,120 | 0 |
| 16 | [`6HkVKYT1...`](https://solscan.io/account/6HkVKYT12fnDSaCWQuARFXvSt8QLQf7974tmqe7iVxWu) | 37.3% | 1,870 | 192 | 3,670 | 0 |
| 17 | [`9gSfXr27...`](https://solscan.io/account/9gSfXr27KyckU3cx9E8Q2htn94f3jhbFpWomfhR7qqqZ) | 38.2% | 1,564 | 195 | 3,153 | 0 |
| 18 | [`AFja5CiN...`](https://solscan.io/account/AFja5CiNHz6iZq4FeYLuiX61AVfHUHgURRLLvdLsxDbD) | 39.0% | 1,453 | 192 | 2,982 | 0 |
| 19 | [`HufuiW43...`](https://solscan.io/account/HufuiW43p5ekUTCmgiHJMqS6JuHcf9jLE5hqDrvyTKHN) | 35.0% | 1,087 | 1045 | 2,645 | 0 |
| 20 | [`A5imfK7P...`](https://solscan.io/account/A5imfK7PFP9YkqTt4g8ToKPsa8xSR3QSmvbwMM4p5xAA) | 37.9% | 1,001 | 176 | 1,965 | 0 |
| 21 | [`Eu1KU118...`](https://solscan.io/account/Eu1KU118rGQEAMnV5uXojfdx6nhozSgNr4Fhxi2suxHB) | 42.7% | 552 | 252 | 1,304 | 0 |
| 22 | [`GZbdS1cQ...`](https://solscan.io/account/GZbdS1cQ4A9yDEJrBavW3dbN5NnnQpvKvtxbjud7LZAm) | 37.3% | 154 | 1297 | 411 | 0 |


## 🎯 Anti-Copier Wash Filters Applied

We FILTER OUT wallets with these GMGN tags:
- ❌ `wash_trader` — Explicitly flagged wash strategies
- ❌ `bundler` — Multi-buy same-block (pump coordination)
- ❌ `snipe_bot` — MEV snipers (unfair edge)
- ❌ `bot` — General bot behavior

## 🔍 Wash Patterns Detected (anti-copier strategies)

For each remaining wallet, we also check for:

1. **Instant roundtrips** — Buy + sell within 5s on same token (+1 each)
2. **High sell/buy ratio** — Sells >85% of buys = dumping on copiers (+3)
3. **Bundled buys** — Same-block multiple buys = coordinated (+2 each)
4. **Small-buy-large-sell trap** — Avg buy <$20, any sell >$500 (+2)
5. **High frequency trader** ⚡ — Avg interval <2 min between trades = bot/sniper (+4)
6. **Same-token repeat flipper** 🔁 — 3+ side flips on same token in 5 min = flippping (+3 per token)

Any wallet with `wash_score >= 5` is excluded.

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
