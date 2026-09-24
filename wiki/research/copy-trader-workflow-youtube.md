# YouTube Workflow: Finding Profitable Copy-Trading Wallets

## Two-Step Workflow

### Step 1: Find Top Performing Tokens
- Use AFK.fun (auto sniper with backtest)
- Backtest: buy every pump.fun token within first 2 min
- Take-profit filter: 10000% (100x)
- 5 tokens out of 19,000 do 100x in 2 days
- Verify each looks legit (5-min chart)

### Step 2: Find Profitable Traders (GMGN Radar)
- gmgn.ai > Copy Trade > Radar
- Input top tokens, get wallets that bought all
- Filter: Highest Profit, exclude volume bots (3000+ txs/week)
- Targets:
  - Realistic 7d P&L >5%
  - Hold time >6 minutes
  - Win rate >40%

## Paid Tool (CopyTrader.com) — More Powerful
- Wallet indices (13,500+ Solana wallets)
- Per-token tools:
  - Early buyers (insiders)
  - Latest buyers (current activity)
  - Small buyers (<$70 — minimal slippage)
  - Top traders by P&L
- Bulk wallet analyzer:
  - Positive ROI required
  - Win rate >40%
  - SOL balance >0.3
  - Median hold time >6 min
  - Total trades >11

## Strategy Validation (Critical)
- CSV generator: exports price history for every trade
- Strategy analyzer: 120,000 entry/TP/SL combinations
- Find optimal: TP 320%, SL 10-15%, trailing stop 50%
- Best result example: 33% win rate, 38% ROI, then 68% with trailing

## Key Insights For Us
1. Find tokens that did 100x (real winners)
2. Find wallets that bought those tokens early/right
3. Filter: real balance + normal frequency + decent ROI
4. Validate with backtest before risking money
5. Use small trade sizes (<$70) to minimize slippage

## Why Our Approach Failed
- We picked wallets based on GMGN smart_money signal
- But those wallets may not have caught the actual 100x winners
- We need to find tokens that 100x'd FIRST, then see who caught them

## Action Plan
1. Find recent pump.fun tokens that did 100x+
2. Use GMGN to find wallets that bought those specific tokens
3. Verify wallet is real (RPC check)
4. Backtest if we could have copied profitably
5. Only add wallets with positive backtest results
