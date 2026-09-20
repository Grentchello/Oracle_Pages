#!/usr/bin/env python3
"""Re-check tx count for the 110 small-PnL wallets with rate-limited retry."""
import json, time, urllib.request, sys
from pathlib import Path

TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
RPC_CHECK = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_rpc_seq.json"))
TX_OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count_v2.json")

# Wallets with 5-20 SOL PnL that exist on-chain
target = []
for w, ts in TRADES.items():
    total_pnl = sum(t["pnl_sol"] for t in ts)
    if 5 <= total_pnl <= 20 and RPC_CHECK.get(w) is True:
        target.append((w, total_pnl))

print(f"Target wallets to recheck: {len(target)}", flush=True)

if TX_OUT.exists():
    tx_data = json.load(open(TX_OUT))
else:
    tx_data = {}

# Skip ones already with successful data (not 429 error)
remaining = []
for w, _ in target:
    if w in tx_data and "error" not in tx_data[w]:
        continue
    remaining.append((w, _))

print(f"Need to fetch/retry: {len(remaining)}", flush=True)

RPC = "https://api.mainnet-beta.solana.com"
current_time = int(time.time())
thirty_days_ago = current_time - 30 * 86400

for i, (addr, pnl) in enumerate(remaining):
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [addr, {"limit": 1000}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read())
            sigs = d.get("result", [])
        
        if not sigs:
            tx_data[addr] = {"total_txs": 0, "recent_txs_30d": 0}
        else:
            recent = sum(1 for s in sigs if s.get("blockTime", 0) > thirty_days_ago)
            tx_data[addr] = {
                "total_txs": len(sigs),
                "recent_txs_30d": recent,
                "first_tx_time": sigs[-1].get("blockTime", 0) if sigs else 0,
                "last_tx_time": sigs[0].get("blockTime", 0) if sigs else 0,
            }
    except Exception as e:
        tx_data[addr] = {"error": str(e)[:100]}
    
    if (i + 1) % 10 == 0:
        TX_OUT.write_text(json.dumps(tx_data))
        active = sum(1 for v in tx_data.values() if v.get("recent_txs_30d", 0) > 0)
        print(f"[{i+1}/{len(remaining)}] {active} active of those rechecks", flush=True)
    
    time.sleep(1.5)  # Slow to avoid 429

TX_OUT.write_text(json.dumps(tx_data))
active = sum(1 for v in tx_data.values() if v.get("recent_txs_30d", 0) > 0)
print(f"\nDONE: {len(tx_data)} wallets, {active} active in 30d")
