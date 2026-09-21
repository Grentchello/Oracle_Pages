# Copy-Trading Methodology from YouTube

**Source**: https://www.youtube.com/watch?v=R3oM7tqzM1s

**Captured**: 2026-09-20

## Key Insight: Why Top GMGN Wallets Fail

1. **Public wallets get crowded** — top leaderboard wallets have many copy traders
2. **When leader buys, copy traders buy → price spikes 3.58K → 4.61K**
3. **Leader sells a few seconds later** — copy traders get sandwiched, lose 25-45%
4. **Leader farms the copy traders** — slowly grows their account at their expense
5. **Large buy sizes** (5-10 SOL) by leader alone drive price up
6. **Short holds** (a few seconds to 20-30 seconds) = designed for farming

## The Solution: FRESH WALLETS

The video's actual methodology:

### Setup Filters in GMGN "Migrated"

- **Launchpad**: specific ones selected by video creator
- **Total Global Fees**: minimum 10 (organic, not scams)
- **Apply filters**

### Find Each Token's Top Fresh Wallets

For each token:
1. Click into token
2. Go to **Top Traders → Fresh**
3. Look for wallets funded recently (days ago) that are profitable

### Selection Criteria (Wallet-Level)

**Required:**
- ✅ Recently funded (days, not weeks/months)
- ✅ Already profitable (+$800, +3K examples)
- ✅ Average buy size **under $100** (won't drive price up too much)
- ✅ Holds tokens for >1 minute (not farmer pattern)
- ✅ Profitable trades vs losers mix (40% WR example — high risk/reward is ok)
- ✅ **No copy traders** of their own (don't farm others)
- ✅ Not copying anyone else (trades solo)
- ✅ Win rate + PnL positive

**Avoid:**
- ❌ Multi-wallet operators (4 wallets same person = price manipulation when buying)
- ❌ Wallets with copy traders following them (already being farmed)
- ❌ Wallets with huge buy sizes (drive price)
- ❌ Wash trader patterns

### Why Fresh Wallets Work

- ✅ Don't have many copy traders yet (you get better entry)
- ✅ Actually trading skill (not farming)
- ✅ Don't have a "popular reputation" to maintain
- ✅ Likely to disappear (fund to MEXC) once profitable → keeps them small
- ✅ Better risk/reward profile for small accounts

### Copy Trade Setup (TradeWiz Bot)

The video recommends setting up:
- **Buy size**: same min/max (e.g., 75 SOL min, 75 SOL max)
- **Anti-PVP**: enable — pauses copy if target sells within 10 seconds
- **Copy sells**: enabled
- **Sell proportionally**: enabled (mirror target sells)
- **Slippage**: 30%
- **Anti-rug**: skip unannounced/unburned tokens

### Telegram Bot Recommendation

TradeWiz (the bot from the video) has copy trading feature.

## Note

Even with these criteria, the video acknowledges:
- Fresh wallets "rotate" — they send funds back to MEXC after profit and create new ones
- This means yesterday's wallet might disappear tomorrow
- Need to keep refreshing the list regularly

## Our Approach

Apply this methodology on our 873 wallets to find ones that fit:
1. Recently active (in last 30d)
2. Average buy size unknown without per-trade breakdown — but we can estimate
3. Holds tokens (not instant sellers) — measure min time between buy and sell
4. Are NOT multi-wallet operators (would need heuristic)
5. Are NOT being copied by others (would need webhook data)
