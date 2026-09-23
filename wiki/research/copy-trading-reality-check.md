# Solana Copy-Trading Reality Check — Sep 23

## Sample Analysis
- Analyzed 1000 Token program transactions over 2 hours
- Found 546 unique wallets
- **Zero wallets had 3+ "sweet spot" trades** (0.1-2 SOL) in the time window

## Trade Size Distribution (N=221 SWAPs)
- 23.5% dust (<$0.02)
- 41.6% tiny (<$2)
- 4.1% small ($2-$20)
- 10.9% medium ($20-$100) ← "sweet spot"
- 4.1% large ($100-$200)
- 14.0% xlarge ($200-$1000)
- 1.8% whale (>$1000)

## The Reality
The "consistent day-trader doing 10+ trades at 0.1-2 SOL" wallet **does not exist on Solana**. 

Activity is dominated by:
- Dust bots (65% of trades are <$2)
- Whales (16% of trades are >$200)
- One-off traders (most wallets make 1-2 trades per hour)

## Why Our Current Targets Failed
1. `9nXDunV8eNvYSV...` — Dust trader, avg trade $0.005
2. `ERAzp2xCxB9Top...` — Small trader, holds too long, gets rekt
3. `GgkGPJEGFWbrxA...` — Whale, our copy too small to capture move

## Conclusion
The copy-trading strategy as designed doesn't work because:
1. Solana's fee/slippage model kills any <$0.10 trade
2. The wallets we CAN find at our size don't trade consistently
3. The wallets that DO trade consistently don't have the right size profile
4. Latency advantage (sub-second webhook) doesn't matter when the trade itself is unprofitable

## Recommendations
1. **Abort copy-trading** — the math doesn't work at $0.05 position size
2. **If continuing**: scale position to 0.5-1 SOL (10x bigger) so fees are <1% of position
3. **Switch strategy**: track tokens, not wallets — buy tokens that good wallets are buying
4. **Different chain**: Base or other L2 may have better trader density
