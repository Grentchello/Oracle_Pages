#!/usr/bin/env python3
"""Pure batched Solana RPC check: do all 873 wallets exist on-chain?"""
import json, time, sys, urllib.request
from pathlib import Path

TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_rpc_check.json")

wallet_pnl = {w: sum(t["pnl_sol"] for t in ts) for w, ts in TRADES.items()}
sorted_wallets = sorted(wallet_pnl.keys(), key=lambda w: wallet_pnl[w], reverse=True)

# Load existing
if OUT.exists():
    results = json.load(open(OUT))
else:
    results = {}

RPC = "https://api.mainnet-beta.solana.com"
BATCH = 50  # 50 addresses per RPC call (Solana limit is 100)

remaining = [a for a in sorted_wallets if a not in results]
print(f"Total: {len(sorted_wallets)}, Already checked: {len(results)}, Remaining: {len(remaining)}", flush=True)

for i in range(0, len(remaining), BATCH):
    batch = remaining[i:i+BATCH]
    
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getMultipleAccountsInfo",
            "params": [batch, {"encoding": "base64"}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            d = json.loads(resp.read())
            values = d.get("result", {}).get("value", [])
            for addr, val in zip(batch, values):
                # val is null if account doesn't exist
                results[addr] = val is not None
    except Exception as e:
        for addr in batch:
            results.setdefault(addr, None)
        print(f"  Batch {i//BATCH + 1} error: {e}", flush=True)
    
    if (i // BATCH + 1) % 5 == 0:
        # Save progress
        OUT.write_text(json.dumps(results))
        exists = sum(1 for v in results.values() if v is True)
        phantom = sum(1 for v in results.values() if v is False)
        unknown = sum(1 for v in results.values() if v is None)
        print(f"  Batch {i//BATCH + 1}: {len(results)} done ({exists} exist, {phantom} phantom, {unknown} unknown)", flush=True)
    
    time.sleep(0.5)

OUT.write_text(json.dumps(results))
exists = sum(1 for v in results.values() if v is True)
phantom = sum(1 for v in results.values() if v is False)
unknown = sum(1 for v in results.values() if v is None)
print()
print(f"DONE: {len(results)} wallets checked")
print(f"  EXIST on Solana: {exists}")
print(f"  PHANTOM (no account): {phantom}")
print(f"  UNKNOWN (RPC error): {unknown}")
