# Copy-Trading Wallet Search — Final Analysis

## Search Methods Tried (Sep 23)

### 1. Smart Money Signal Wallets
- 30 wallets found
- All do 1000+ txs/day (bots)
- Trading dust sizes
- ❌ NOT SUITABLE

### 2. Top Traders on Trending Tokens
- 13 wallets found
- Multi-token, real sized
- But all show -50% to -90% candle moves
- ❌ The targets catch moonshots OR die - we get the die part

### 3. Top Holders of Established Tokens (>30d old)
- 5 multi-token holders found
- BUT they're CEX/treasury wallets (transfers only, no swaps)
- ❌ Not active traders

### 4. Active Traders on Established Tokens
- 1 multi-token real-sized trader found
- dmuXAmcXJcdNuK - 4632 SOL balance, but 1000 txs/day = BOT
- ❌ Bot, not human

### 5. Smaller Established-Token Active Traders
- ~5 candidates found
- Most are single-token
- Trade size typically too small or too few round trips

## Conclusion

The Solana memecoin space is dominated by:
1. **Dust sniper bots** (1000+ txs/day, $0.01 trades)
2. **CEX/treasury wallets** (high balance, transfers only)
3. **Active bot traders** (high frequency, real size)
4. **Real human traders** who:
   - Are rare
   - Trade volatile new tokens
   - Get rugged frequently
   - Don't hold positions long enough to be profitable to copy at our size

## Path Forward Options

### A. Copy-trade existing winners anyway
- Accept 80% dump rate
- Need much bigger positions (0.5+ SOL) to absorb losses
- Or stop-loss to cut losers early
- The 5.4% profitable run we had came from 3 moonshot trades out of 164

### B. Different strategy entirely
- Token-based bot (existing memecoin scanner) - works for momentum
- Liquidity provision (LP) - earn fees
- Sniping new launches ourselves (we choose which tokens)

### C. Hybrid
- Use webhook infrastructure to detect when wallets sell
- Don't copy their buys - use them as exit signals for OUR positions
- We pick the tokens via our bot, they tell us when to sell

The user has explicit preferences: "copy wallets, not tokens" — but the data shows it's not viable at our scale.
