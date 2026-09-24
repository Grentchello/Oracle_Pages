# Copy-Trading Awareness — Lessons Learned

## Things To Be Aware Of (Updated Sep 24)

### Wallet Selection Gotchas
- **30d PnL is misleading**: wallets can show positive PnL by farming 100s of dust positions for tiny gains
- **Early buyer ≠ profitable**: DcryhRtJTcWeNs... had -7.92% PnL despite being EARLY (bought before our targets)
- **Most copy-trading targets are net negative**: 33% win rate is common but still results in losses
- **GMGN "smart money" tags are unreliable**: includes bots, dust traders, and unprofitable wallets
- **Phantom wallet data**: GMGN returns fabricated data under rate-limit recovery — always verify via RPC

### Execution Gotchas
- **Position size (0.05 SOL) too small**: can't capture real edge
- **Slippage + fees = ~1.2% loss per round trip**: kills tiny targets
- **Webhooks are sub-200ms but the trader's wallet is rate-limited**: public RPC throttles
- **Wallet discovery sample size matters**: 50 sigs only catches single-token traders
- **Multi-token filter is rare**: most "active" wallets are single-token bots

### Token-Level Gotchas
- **Volatile memecoins rug -50% to -90%**: regardless of entry timing
- **New launches = instant rugs**: even good timing can't save you
- **Trending ≠ stable**: trending tokens often have highest volatility
- **Dust tests by smart wallets**: most "signals" are $0.01 test buys, not real positions

### Strategy Gotchas
- **Copy-trading 1000+ txs/day wallets = death**: dust fees eat everything
- **Following copiers = circular signal**: bots following bots following bots
- **Win rate alone doesn't predict profit**: need avg win > avg loss
- **"Smart money" tags include snipers, not just alpha holders**

## What Actually Worked

### Real human traders (5-50 txs/day, 1+ SOL balance)
- 3 originals were net positive: BjNyQWnf5c98Sv (+222), FHkuAETEg19j2w (+122), BcK9oWZwJBo48z (-6)
- Profitable through volume not skill: small per-trade wins

### Real-time copy infrastructure
- Sub-200ms webhook latency (vs 51s polling)
- Helius RPC faster than public Solana RPC
- Cloudflare tunnel for webhook exposure

## What Didn't Work

### Most "profitable" wallets were net losers
- 80% of trades hit -50%+ candle moves
- Even when targets made profit, our slippage ate gains
- Position size too small to capture moonshots

### "Early buyer" discovery was flawed
- Buying before others doesn't mean buying profitably
- Many early buyers are still getting rugged
- DcryhRtJTcWeNs example: -7.92% PnL

## Honest Conclusion

Copy-trading at 0.05 SOL position size is a losing strategy.
- Fees + slippage = -1.2% per round trip
- Even profitable wallets only net +1.5 mSOL per trade
- Win rate of 33% = negative expected value

Future options:
- Increase position size (need 0.5+ SOL to absorb fees)
- Trade less frequently (only copy high-conviction signals)
- Different strategy entirely (token-based, LP, sniping)
