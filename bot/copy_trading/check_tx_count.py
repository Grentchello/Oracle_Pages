#!/usr/bin/env python3
"""For each real on-chain wallet, count transactions in last 30 days."""
import json, time, urllib.request, sys
from pathlib import Path

RPC_OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_rpc_seq.json")
TX_OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count.json")

rpc = json.load(open(RPC_OUT))
real_wallets = [a for a, v in rpc.items() if v is True]

# Load existing
if TX_OUT.exists():
    tx_counts = json.load(open(TX_OUT))
else:
    tx_counts = {}

RPC = "https://api.mainnet-beta.solana.com"

remaining = [a for a in real_wallets if a not in tx_counts]
print(f"Real wallets: {len(real_wallets)}, checked: {len(tx_counts)}, remaining: {len(remaining)}", flush=True)

# Get current time
import datetime
current_time = int(time.time())
thirty_days_ago = current_time - 30 * 86400

for i, addr in enumerate(remaining):
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [addr, {"limit": 1000}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            sigs = d.get("result", [])
            
            # Count recent (last 30 days)
            recent_count = sum(1 for s in sigs if s.get("blockTime", 0) > thirty_days_ago)
            total_count = len(sigs)
            
            tx_counts[addr] = {
                "total_txs": total_count,
                "recent_txs_30d": recent_count,
                "first_tx_time": sigs[-1].get("blockTime", 0) if sigs else 0,
                "last_tx_time": sigs[0].get("blockTime", 0) if sigs else 0,
            }
    except Exception as e:
        tx_counts[addr] = {"error": str(e)[:100]}
        continue
    
    if (i + 1) % 50 == 0:
        TX_OUT.write_text(json.dumps(tx_counts))
        # Quick stats
        no_tx = sum(1 for v in tx_counts.values() if v.get("total_txs", 0) == 0)
        has_tx = sum(1 for v in tx_counts.values() if v.get("total_txs", 0) > 0)
        print(f"[{i+1}/{len(remaining)}] {has_tx} have tx, {no_tx} have 0 tx", flush=True)
    
    time.sleep(0.1)

TX_OUT.write_text(json.dumps(tx_counts))
no_tx = sum(1 for v in tx_counts.values() if v.get("total_txs", 0) == 0)
has_tx = sum(1 for v in tx_counts.values() if v.get("total_txs", 0) > 0)
real_trader = sum(1 for v in tx_counts.values() if v.get("recent_txs_30d", 0) > 0)
print(f"\nDONE: {len(tx_counts)}/{len(real_wallets)}")
print(f"  Zero transactions ever: {no_tx}")
print(f"  Has transactions: {has_tx}")
print(f"  Real trader (recent 30d): {real_trader}")
