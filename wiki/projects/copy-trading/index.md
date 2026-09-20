# 📊 Copy-Trading

**Goal:** Find wallets with proven track record. Monitor their activity to decide what to follow.

## 🧠 Smart Money Wallet List

**139 wallets** found from 8 recently-completed Pump.fun tokens. Top 100 ranked by total realized PnL across winning tokens.

[📊 **Open Live Dashboard** →](./dashboard.html)

**Top 10:**

| # | Wallet | Total PnL (SOL) | Tokens |
|---|--------|-----------------|--------|
| 1 | `864PisFm...dc2L` `→` [full](https://solscan.io/account/864PisFmdkCDpPR5J6jhMZCRzHZc5LsoaDTsG4hndc2L) | +4930 | 1 |
| 2 | `DrPkRQWb...CPej` `→` [full](https://solscan.io/account/DrPkRQWbQ9ybEUciW4QgmPbscEDhsvcpTMkfr7HSCPej) | +3954 | 1 |
| 3 | `h53FRcCH...yHZy` `→` [full](https://solscan.io/account/h53FRcCHDp82odsd4i23KeVV3ibgLk5ggvdYCfLyHZy) | +3409 | 1 |
| 4 | `Biz5FKp5...rJYp` `→` [full](https://solscan.io/account/Biz5FKp5SjNMUasTCM7FTydwFkWJVYofLSnX8RhJrJYp) | +3175 | 1 |
| 5 | `Bg2pmUcU...U9yU` `→` [full](https://solscan.io/account/Bg2pmUcUj3CTs6QBfzgVq1ej9xLL9aQs3A9wAgrxU9yU) | +3031 | 1 |
| 6 | `CRSGqhoj...2nP9` `→` [full](https://solscan.io/account/CRSGqhoju16LuHYR8SvKTVvJ63ZG15mymCXV9spi2nP9) | +2381 | 1 |
| 7 | `8ynNvNq3...Cykm` `→` [full](https://solscan.io/account/8ynNvNq3pC1T94RmBQAatpnaUwWBvrh2EdEdzwCxCykm) | +2347 | 1 |
| 8 | `9vjRjbws...HGF6` `→` [full](https://solscan.io/account/9vjRjbwsV8EdKm8J89ZUdHDduVGZtSiDvC2KkikxHGF6) | +1774 | 1 |
| 9 | `3f67RzmH...VY3j` `→` [full](https://solscan.io/account/3f67RzmHqWznN1kwbAfsrtfh4eMsWEu2GTuXGv8FVY3j) | +1771 | 1 |
| 10 | `7fTVgAze...Ewpn` `→` [full](https://solscan.io/account/7fTVgAzegWbk6bQL1HXoHEKBjDbdD3jjkmnTAtiiEwpn) | +1543 | 1 |


*Generated 2026-09-20T03:19:58Z. Full data in [dashboard.html](./dashboard.html).*

---

## 🚧 Investigation Status (Sep 20)

After extensive filtering, we have now built a **smart money wallet list**:

**What we tried:**
1. ✅ Top traders leaderboard (GMGN) — found wallets but all high-frequency
2. ✅ Smart-money tagged trades — same issue
3. ✅ Early buyers of tokens that pumped — only one-shot snipers
4. ✅ High-frequency filtering (<50/day)
5. ✅ Wash pattern detection (8 different patterns)
6. ✅ Bridge/aggregator detection
7. ✅ **Token-first discovery** — pull winners from recently-completed Pump.fun tokens

**Current approach:**
- Pull tokens with smart-degen count ≥ 20 (proven "smart money" presence)
- Extract top traders (positive realized PnL) from each
- Rank unique wallets by total profit

**Next directions:**
- Scan 50+ tokens (only 8 done so far due to rate limits)
- Find wallets that win on MULTIPLE tokens = true smart money
- Verify with full GMGN stats (win rate, frequency)
- Set up live monitoring for top 10-20 wallets
