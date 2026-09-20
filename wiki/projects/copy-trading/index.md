---
title: Copy-Trading Wallet Discovery
type: project
status: live
date: 2026-09-20
---

# 🔍 Copy-Trading Wallet Discovery

**Goal**: Find Solana wallets that are profitable to copy-trade, while filtering out anti-copier wash strategies.

**Last scan**: 2026-09-20T00:32:04Z
**Chain**: Solana
**Window**: 30-day stats (GMGN doesn't support 60d natively)

## 📊 Current Top 27 Traders (sorted by 60-day proxy score)

**Scoring formula**: `realized_profit × (win_rate / 100) × log(unique_tokens + 1) − wash_score × 10`

| # | Wallet | Win Rate | PnL 30d (SOL) | Tokens | Score | Wash |
|---|--------|----------|---------------|--------|-------|------|
| 1 | [`AJofLRzr...`](https://solscan.io/account/AJofLRzr9Hj6P86u2pQuxhLM12ZaMupRtxMDmyAJ18KN) | 36.4% | 182,019 | 985 | 457,193 | 0 |
| 2 | [`9haKJini...`](https://solscan.io/account/9haKJiniE7HR5im7b9a74VUGD7vHDu6waBwAdQegwqQm) | 69.3% | 19,975 | 336 | 80,540 | 0 |
| 3 | [`DULT2qC5...`](https://solscan.io/account/DULT2qC5mH15gxTKbrFgxEVHrNeKbkAkNYoq4gU5knL8) | 54.7% | 13,641 | 1717 | 55,615 | 0 |
| 4 | [`7bRKHriC...`](https://solscan.io/account/7bRKHriCHw5keDPPsTXx8vWZo3npMtuGeevMyMEseUTb) | 53.7% | 13,908 | 1518 | 54,729 | 0 |
| 5 | [`EnQdeYsy...`](https://solscan.io/account/EnQdeYsyhacWWDuWfFJvtyk1ehD1cB511ujxJpUtiiWA) | 36.1% | 20,812 | 1167 | 53,058 | 0 |
| 6 | [`Dnq77xMN...`](https://solscan.io/account/Dnq77xMNwqPTj8NRhXvD827HNJNgQvZpqob3oMFus7tE) | 58.5% | 11,886 | 1322 | 49,996 | 0 |
| 7 | [`46cSe3pb...`](https://solscan.io/account/46cSe3pbpyqzENHgvie4FnYvYPsYJQUVX1oSnPNc4xBZ) | 35.8% | 19,679 | 1088 | 49,279 | 0 |
| 8 | [`Gainsdr1...`](https://solscan.io/account/Gainsdr1kr3bEm5v3NV782v5PgrZD5QHhhcV2zRsYetS) | 60.7% | 13,174 | 332 | 46,420 | 0 |
| 9 | [`H3rUiKEF...`](https://solscan.io/account/H3rUiKEFPnTM6CHCmJqKt4Nd1xeFATK9aUmU4sbD5za7) | 61.1% | 9,234 | 1235 | 40,189 | 0 |
| 10 | [`77XV9rBi...`](https://solscan.io/account/77XV9rBiwk6WAXjzTWiwtCQfmB6CXsw1j7Kp3G5xUyez) | 35.0% | 14,829 | 1209 | 36,794 | 0 |
| 11 | [`EyMEijA6...`](https://solscan.io/account/EyMEijA6r9MePsvDv5Vu7WphrXenmXWJ1HzHsm5WDcr) | 64.3% | 9,401 | 328 | 35,028 | 0 |
| 12 | [`9tY7u1Hg...`](https://solscan.io/account/9tY7u1HgEt2RDcxym3RJ9sfvT3aZStiiUwXd44X9RUr8) | 30.4% | 13,790 | 2117 | 32,097 | 0 |
| 13 | [`C86oRMyU...`](https://solscan.io/account/C86oRMyUqzsXKXEAsCUbrhJuYuMbqXxE886s9MpUFF88) | 68.5% | 6,151 | 971 | 28,991 | 0 |
| 14 | [`DyNiyDgY...`](https://solscan.io/account/DyNiyDgYg3A4sHKXFLccUEVHX3zBDGxx1m7xtqxnKjKP) | 55.0% | 7,277 | 932 | 27,364 | 0 |
| 15 | [`9bPSz9QG...`](https://solscan.io/account/9bPSz9QGH62BD8YQarZEnfCmNk6kXGMoGgTxFVxcYZfU) | 38.7% | 9,497 | 572 | 23,333 | 0 |
| 16 | [`HbYd46DF...`](https://solscan.io/account/HbYd46DFHe7vLRGKW122XDPiUzcxLw4g8hPUtwfCNpV2) | 37.5% | 8,740 | 570 | 20,829 | 0 |
| 17 | [`4fNDW8qe...`](https://solscan.io/account/4fNDW8qeWdWQMdtZ6ro8kkK49ZAHtiAtzcJbFvgxNcVZ) | 36.9% | 8,566 | 572 | 20,090 | 0 |
| 18 | [`Cwczs8JS...`](https://solscan.io/account/Cwczs8JSCXf1YSqk6pWWNWb9yExJuKbAdTPepPjx1RBH) | 58.1% | 4,410 | 923 | 17,493 | 0 |
| 19 | [`7PEGXoeq...`](https://solscan.io/account/7PEGXoeq5EF37HLt2XERzKD2RaZyVh2zh5dgAE8NsLmP) | 63.2% | 3,890 | 1208 | 17,449 | 0 |
| 20 | [`8auBVoCF...`](https://solscan.io/account/8auBVoCFGe8SetWGZABiXAR91xNZ7kMqJLPvtvZe8aSq) | 33.1% | 7,066 | 713 | 15,385 | 0 |
| 21 | [`5F4NuBte...`](https://solscan.io/account/5F4NuBte8QRfUH8HtggYMLBzTUKtYARmRVmkb1Ah7xqR) | 48.0% | 3,816 | 275 | 10,287 | 0 |
| 22 | [`GHoJLEzi...`](https://solscan.io/account/GHoJLEzik3QrdFBEEYUvhHi3f12PQ2ZC3Eg99ACebh9z) | 53.9% | 2,463 | 344 | 7,758 | 0 |
| 23 | [`DeSvhVxb...`](https://solscan.io/account/DeSvhVxbNyjcQQ1oRPK7eGuSMujiNZw1gtZXYu8QFQMa) | 41.5% | 1,289 | 2004 | 4,066 | 0 |
| 24 | [`3DnwtnkP...`](https://solscan.io/account/3DnwtnkPxgCEmaxcpYviEUNFqoED6X2icoY2KdhLXaQS) | 52.4% | 1,005 | 545 | 3,321 | 0 |
| 25 | [`HufuiW43...`](https://solscan.io/account/HufuiW43p5ekUTCmgiHJMqS6JuHcf9jLE5hqDrvyTKHN) | 35.0% | 1,087 | 1044 | 2,648 | 0 |
| 26 | [`A5imfK7P...`](https://solscan.io/account/A5imfK7PFP9YkqTt4g8ToKPsa8xSR3QSmvbwMM4p5xAA) | 37.1% | 959 | 175 | 1,837 | 0 |
| 27 | [`Eu1KU118...`](https://solscan.io/account/Eu1KU118rGQEAMnV5uXojfdx6nhozSgNr4Fhxi2suxHB) | 42.5% | 384 | 249 | 902 | 0 |


## 🎯 Anti-Copier Wash Filters Applied

We FILTER OUT wallets with these tags:
- ❌ `wash_trader` — Explicitly flagged wash strategies
- ❌ `bundler` — Multi-buy same-block (pump coordination)
- ❌ `snipe_bot` — MEV snipers (unfair edge)
- ❌ `bot` — General bot behavior

## 🔍 Wash Patterns Detected (anti-copier strategies)

For each remaining wallet, we also check for:

1. **Instant roundtrips**: Buy + sell within 5s on same token
2. **High sell/buy ratio**: Sells >85% of buys = dumping on copiers
3. **Bundled buys**: Same-block multiple buys (coordinated)
4. **Small-buy-large-sell trap**: Avg buy <$20, any sell >$500

Any wallet with `wash_score >= 5` is excluded.

## ⚠️ Caveats

- **GMGN only provides 30-day stats** — we use score weighting as a 60d proxy
- **Wallets with `top_renamed` / `top_followed` tags** may be baiting copiers — review before following
- **High PnL + low win rate** (#1) suggests volume-based strategy (risky to copy)
- **High win rate + low PnL** suggests small positions (less interesting)

## 🔧 Next Steps

1. **Continuous monitoring**: Poll these wallets every 60s for new trades
2. **Build SKIP list**: Tokens these wallets bought and rugged
3. **Live copy-trade**: When user re-enables Solana bot, copy top 5 wallets
4. **Refresh**: Run `wallet_discovery.py` weekly to update watchlist

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
