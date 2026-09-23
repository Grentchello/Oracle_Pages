# Solana RPC Rate Limits — Field Notes

**Recorded**: 2026-09-23 12:49 UTC
**Context**: Copy-trading wallet discovery + trader polling

## Public RPC (`https://api.mainnet-beta.solana.com`)

### Limits Observed

- **Per-second burst**: ~50 RPC requests before hitting 429
- **Sustained rate**: ~5-10 req/s sustained before throttling
- **Cool-down after burst**: 60-120 seconds for limit reset
- **Hard ban**: GMGN API reports "IP is temporarily banned" after sustained abuse (lasted minutes)

### Endpoints

- `getAccountInfo`: fast, ~1s
- `getBalance`: fast, ~1s
- `getSignaturesForAddress`: rate-limited faster — 10 calls in 30s triggers throttling
- `getTransaction`: slowest — large response bodies, ~2-5s per call

### Error Modes

- HTTP 429 with body `{"code":429, "message":"Too Many Requests"}`
- `WrongSize` error on `getTransaction` for sigs with too many accounts (truncation)
- `Invalid param: WrongSize` on cached responses after rate-limit cooldown
- Empty result `{"result": null}` during throttling

## GMGN API (public, free tier)

### Limits Observed

- `market trenches` endpoint: ~10 calls/min sustained
- `token traders`: rate-limited after 50-100 calls/hour
- **Hard ban**: "IP is temporarily banned" after ~100 calls in short burst (lasts 5-10 min)
- **CRITICAL**: Returned phantom wallet data on rate-limit recovery — corrupted responses

## Rate Limit Strategies That Work

### 1. Sequential + Slow

```python
import time

for token in tokens:
    data = get_traders(token)
    save(data)
    time.sleep(0.2)  # 5 req/sec max
```

Got ~50 unique wallets before hitting 429.

### 2. Resume After Cooldown

```python
def get_traders_resume(tokens, save_path):
    done = load_done(save_path)
    for token in tokens:
        if token in done: continue
        data = get_traders(token)
        if data:
            done[token] = data
            save(done)
            time.sleep(0.2)
        else:
            # Rate limited
            time.sleep(60)
            continue
```

Processed 108 tokens in batches with 60s cooldowns.

### 3. Single Block Pull (Most Efficient)

```python
# Pull ALL recent txs in one block
block = rpc.getBlock(slot, "signatures")  # Returns just sigs, no bodies
# Then parse for Token program interactions
# Get signers = real wallet addresses
# 1 RPC call → 3000 sigs → filter for Pump.fun → ~1000 unique traders
```

Got **3000 sigs in ONE call** vs 50 calls/100 wallets with the per-wallet approach.

### 4. Token Program Filter

Querying `TokenkegQ...` program signatures returns ALL token activity — every swap, every transfer, every mint interaction. From these:
- Extract fee payers (signers) = traders
- Filter by `recent_blockhash` for fresh activity
- Verify each via RPC `getAccountInfo` (cheap)

## Cost vs Free Comparison

| Source | Cost | Rate | Coverage |
|--------|------|------|----------|
| Public RPC | Free | 5-10 req/s | All chains, all txs |
| GMGN free | Free | 10/min | Top traders, smart money (broken) |
| Birdeye paid | ~$50/mo | Higher | Better wallet data |
| Helius free | Free (limited) | Higher | Webhooks for real-time |
| Triton One | Pay per call | Unlimited | Production-grade |

## Copy-Trading Specific Findings

### Real Wallet Discovery Pipeline (Working)

1. **Get recent Token program sigs** (1 RPC call, 3000 sigs)
2. **Extract unique fee payers** (Python, instant) → ~1000 wallets
3. **Filter by activity recency** (1 RPC call per wallet) → ~100 active
4. **Check SOL balance + token accounts** (1 RPC call per wallet) → ~20-50 real, active

**Cost**: ~100-200 RPC calls per discovery cycle

### Trader Polling

- **Per wallet**: 1 `getSignaturesForAddress` call per 2s
- **24 wallets**: 12 calls/sec sustained
- **6 wallets**: 3 calls/sec sustained (safe)
- **Public RPC free tier cannot sustain 24 wallets**

### Recommended Architecture

- **Discovery**: Run once per 1-4 hours, batch-pull sigs, save to cache
- **Trader**: Track 6-10 wallets max to stay under rate limit
- **Backup RPC**: Use a paid provider (Helius/QuickNode) for production

## Recovery From Rate Limit

1. **Wait 60-120 seconds** (transient throttle)
2. **Switch endpoint** (e.g. mainnet → mainnet-beta if available)
3. **Use cached responses** (don't re-fetch what you have)
4. **Implement exponential backoff**: 1s → 2s → 4s → 8s → 60s → 300s
5. **Check response headers** — `Retry-After` header often tells exact wait time

## Phantom Wallet Issue (Critical Learning)

**GMGN's `token traders` endpoint returns phantom wallets under rate-limit recovery.** Phantom = address doesn't exist on Solana (`getAccountInfo` returns null).

This means:
- Don't trust any single source
- Always verify via RPC
- If `getAccountInfo` returns null = wallet is fake
- Even when GMGN reports "+$132M PnL" — check it on-chain first

## Trader Specific Notes

### Why The 24-Wallet Trader Stopped Logging

- 24 wallets × 1 RPC call every 2s = 12 calls/sec
- Public RPC allows ~5-10 req/s sustained
- After 5 minutes, trader enters throttle loop, all polls return empty
- Wallet `last_sig` doesn't get updated → next poll returns same sigs → no new trades detected

### Fixes That Work

1. **Reduce wallet count**: 6 wallets = 3 calls/sec (safe)
2. **Increase poll interval**: 10s × 6 wallets = 0.6 calls/sec
3. **Sequential with delay**: 0.5s between wallet polls
4. **Multiple RPC endpoints**: rotate to spread load

### What Doesn't Work

- ❌ Naive parallel polling (rate limited instantly)
- ❌ Aggressive 2s polling on 24 wallets
- ❌ Re-polling same wallets with no state change
- ❌ Retrying failed calls immediately

## Status: Rate Limits Documented

Ready to use later for:
- Higher-capacity discovery (need paid RPC for >50 wallets)
- Better trader scaling (use Helius free or paid RPC)
- Production deployment (Triton One or QuickNode)
