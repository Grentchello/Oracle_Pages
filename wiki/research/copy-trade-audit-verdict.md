
# 20-Min Copy-Trade Audit Verdict

**Conclusion**: The wallets we picked are NOT worth copying.

## Evidence
- 30 trades in ~1 minute of webhook activity
- Win rate: 0% (0 wins, 3 losses in closed trades)
- Balance: 2.0 SOL → 0.74 SOL (-63%)
- Target trade sizes: 0.00001-0.0001 SOL ($0.002-$0.02)
- Our execution: 0.05 SOL per copy

## Pattern
Wallets are trading in dust amounts:
- Most swaps <$0.02 in size
- We're paying 0.6% fees + slippage on $2 trades
- Slippage on a $0.02 target is meaningless but our $0.05 copy still pays fees
- Result: We accumulate fees faster than we capture gains

## Hypothesis Confirmed
The wallets appear to be using copiers as exit liquidity — they make tiny swaps
that generate fee revenue on the platform, while copiers pay real fees on the
mirror trades with no real upside.

## What To Do Next
1. Filter wallets by minimum trade size (e.g. >0.1 SOL per swap)
2. Filter for proven profitability (positive realized PnL over weeks)
3. Use slower polling/webhook for less-active wallets
4. Target 5-15 trades/day wallets instead of 1000+

Updated: 2026-09-23
