# Copy-Trade Wallet Failure Modes — Sep 23

## Bad Features (AVOID These)

### 1. Sniper Behavior (80% of our losses)
- 36/49 trades saw >50% candle drops in our window
- These wallets buy new/risky tokens
- Pattern: catch moonshot or die trying
- At 0.05 SOL our position can't survive the 80% drawdowns

### 2. Dust Spammers (avoided but worth noting)
- 1000+ txs/24h
- <$0.20 per trade
- Real money balance but no real positions
- Pump-fun sniping bots

### 3. Phantom Wallets (avoided)
- Don't exist on-chain
- GMGN returns fabricated data
- Always verify via RPC first

## What Worked (the 5.4% profitable run)

### Real human traders had:
- Balance: 1-6 SOL (real money, not 0.01 SOL)
- Frequency: 9-27 txs/24h (NOT 1000+)
- Avg trade size: $80-300 (real positions)
- Multi-token activity (picks different tokens)

### But they still had problems:
- 80% of trades hit dramatic candle moves (>50% in either direction)
- Either early pump moonshot OR instant rug
- Our 0.05 SOL position size = we get killed on rugs
- Only 3 trades out of 49 had the +200% moves that made the profit

## What We Need Next

### Ideal Wallet Profile
- **Trade size**: 0.5-5 SOL per swap ($100-$1000)
- **Frequency**: 5-50 txs/day (real human, not bot)
- **Balance**: 2-50 SOL (real money)
- **Multi-token**: yes (diversified)
- **PnL**: positive over weeks
- **Token selection**: established/trending tokens (not brand-new launches)
- **Hold time**: minutes to hours, not seconds

### Avoid
- Tokens launched in last 24h (extreme volatility)
- Candle moves >30% during target's trade (rug or pump-and-dump)
- Wallets where >50% of their trades hit dramatic moves
- Wallets doing 100+ txs/day (bots)
- Wallets with <$10 balance (dust)

## Strategy Implications

Our copy-trading needs:
1. Either bigger positions (0.5+ SOL) to absorb 50% drawdowns
2. Or wallets that trade stable tokens (low volatility)
3. Or a stop-loss (sell if price drops 20% from our buy)
4. Or filter tokens (skip ones with recent >50% moves)

The 5.4% profit came from catching 3 moonshot trades (+55%, +200%, +520%).
The 49 closed trades had 36 dumps and only 13 modest gains.
Net positive by accident — the 3 moonshots outweighed the dumps.

## Conclusion

The "smart money" wallets on Solana are mostly:
- Sniper bots OR
- Risk-seeking humans who trade volatile new tokens

Neither profile is suitable for 0.05 SOL copy-trading.
