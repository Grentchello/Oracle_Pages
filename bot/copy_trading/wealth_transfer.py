#!/usr/bin/env python3
"""
Detect 'wealth transfer' / draining pattern in a wallet:
- Multiple outbound SOL transfers in last 30d to different addresses
- Wallet frequently receives then sends out (looks like a bridge/mixer)
- Wallet balance drains steadily

Heuristic: For each wallet, parse recent transactions for SOL transfers.
If significant outflow to many destinations, it's a wealth-transfer wallet.
"""
import json, time, urllib.request, sys
from pathlib import Path

TX_COUNT = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count.json"))
BALANCES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_balance.json"))

# Wallets with balance in target range (5-20 SOL)
target = [(a, v) for a, v in BALANCES.items() 
          if v.get("sol") is not None and 5 <= v["sol"] <= 20]
print(f"Wallets in 5-20 SOL range: {len(target)}")

# Also include all real active wallets just in case
all_active = [(a, v) for a, v in BALANCES.items() 
              if v.get("sol") is not None and v["sol"] > 0]

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_drain.json")
if OUT.exists():
    drain_data = json.load(open(OUT))
else:
    drain_data = {}

# Use getSignaturesForAddress and inspect SOL balance changes
RPC = "https://api.mainnet-beta.solana.com"

remaining = [a for a, _ in all_active if a not in drain_data]
print(f"To analyze: {len(remaining)}")

# For each wallet, check last 20 transactions
for i, addr in enumerate(remaining):
    try:
        # Get recent sigs
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [addr, {"limit": 20}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            sigs = d.get("result", [])
        
        if not sigs:
            drain_data[addr] = {"tx_analyzed": 0}
            continue
        
        # Count SOL changes
        sol_out = 0  # SOL leaving wallet
        sol_in = 0   # SOL entering wallet
        unique_destinations = set()
        unique_sources = set()
        
        # For each signature, fetch transaction and check pre/post balances
        for sig_info in sigs[:10]:  # just first 10 for speed
            try:
                sig = sig_info["signature"]
                req = urllib.request.Request(RPC, data=json.dumps({
                    "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
                    "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
                }).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    tx = json.loads(resp.read())
                    result = tx.get("result", {})
                    if not result:
                        continue
                    
                    msg = result.get("transaction", {}).get("message", {})
                    keys = msg.get("accountKeys", [])
                    
                    if addr not in keys:
                        continue
                    
                    idx = keys.index(addr)
                    pre = result.get("meta", {}).get("preBalances", [0] * len(keys))
                    post = result.get("meta", {}).get("postBalances", [0] * len(keys))
                    
                    if idx < len(pre) and idx < len(post):
                        change = (post[idx] - pre[idx]) / 1e9  # in SOL
                        if change > 0.01:
                            sol_in += change
                        elif change < -0.01:
                            sol_out += abs(change)
                            # Find destination — first other key with positive change
                            for j, (k_idx, bal_change) in enumerate(zip(range(len(pre)),
                                                                          [post[j] - pre[j] for j in range(len(pre))])):
                                if j != idx and bal_change > 0.01:
                                    if j < len(keys):
                                        unique_destinations.add(keys[j])
                                    break
            except Exception:
                continue
        
        drain_data[addr] = {
            "tx_analyzed": len(sigs[:10]),
            "sol_out": sol_out,
            "sol_in": sol_in,
            "unique_destinations": len(unique_destinations),
            "ratio_out_to_in": (sol_out / sol_in) if sol_in > 0 else None,
        }
    except Exception as e:
        drain_data[addr] = {"error": str(e)[:100]}
    
    if (i + 1) % 25 == 0:
        OUT.write_text(json.dumps(drain_data))
        # Quick classifier
        high_drain = sum(1 for v in drain_data.values() 
                         if v.get("sol_out", 0) > 1)  # > 1 SOL out in 10 txs
        print(f"  [{i+1}/{len(remaining)}] {high_drain} high-drain wallets found", flush=True)
    
    time.sleep(0.1)

OUT.write_text(json.dumps(drain_data))
high_drain = sum(1 for v in drain_data.values() if v.get("sol_out", 0) > 1)
print(f"\nDONE: {len(drain_data)} wallets analyzed")
print(f"  High drain (>1 SOL out in last 10 txs): {high_drain}")
