#!/usr/bin/env python3
"""
Find wallets that are:
1. Real traders (had transactions in last 30d)
2. Hold 5-20 SOL (modest trader, similar to our 2 SOL account size)
3. Not draining balance (no major outbound transfers daily)
"""
import json, time, urllib.request, sys
from pathlib import Path

TX_COUNT = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count.json"))

# Filter to wallets that are active (real traders)
active = {a: v for a, v in TX_COUNT.items() 
          if v.get("recent_txs_30d", 0) >= 1}
print(f"Active wallets to check: {len(active)}")

# Sort by tx count - higher = more active
active_sorted = sorted(active.items(), key=lambda x: x[1].get("recent_txs_30d", 0), reverse=True)

RPC = "https://api.mainnet-beta.solana.com"

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_balance.json")
if OUT.exists():
    balances = json.load(open(OUT))
else:
    balances = {}

# Phase 1: get SOL balance for each
print("\nPhase 1: getting SOL balance...")
remaining = [a for a in active if a not in balances]
print(f"Remaining: {len(remaining)}")

for i, addr in enumerate(remaining):
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getBalance",
            "params": [addr]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            v = d.get("result", {}).get("value")
            balances[addr] = {"lamports": v if v else 0,
                              "sol": (v if v else 0) / 1e9}
    except Exception:
        balances[addr] = {"lamports": None, "sol": None}
    
    if (i + 1) % 50 == 0:
        OUT.write_text(json.dumps(balances))
        in_range = sum(1 for v in balances.values() 
                      if v.get("sol") is not None and 5 <= v["sol"] <= 20)
        print(f"  [{i+1}/{len(remaining)}] {in_range} in 5-20 SOL range so far")
    
    time.sleep(0.05)

OUT.write_text(json.dumps(balances))
in_range = sum(1 for v in balances.values() 
              if v.get("sol") is not None and 5 <= v["sol"] <= 20)
below_range = sum(1 for v in balances.values() 
              if v.get("sol") is not None and 0 < v["sol"] < 5)
above_range = sum(1 for v in balances.values() 
              if v.get("sol") is not None and v["sol"] > 20)
no_data = sum(1 for v in balances.values() if v.get("sol") is None)
zero = sum(1 for v in balances.values() if v.get("sol") == 0)

print(f"\nPhase 1 results ({len(balances)} checked):")
print(f"  0 SOL (closed):     {zero}")
print(f"  0-5 SOL:           {below_range}")
print(f"  ✅ 5-20 SOL (TARGET): {in_range}")
print(f"  >20 SOL (whale):   {above_range}")
print(f"  no data:           {no_data}")
