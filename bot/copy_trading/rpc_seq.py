#!/usr/bin/env python3
"""Sequential on-chain existence check, one wallet per call."""
import json, time, urllib.request, sys
from pathlib import Path

TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_rpc_seq.json")

wallet_pnl = {w: sum(t["pnl_sol"] for t in ts) for w, ts in TRADES.items()}
sorted_wallets = sorted(wallet_pnl.keys(), key=lambda w: wallet_pnl[w], reverse=True)

# Load existing
if OUT.exists():
    results = json.load(open(OUT))
else:
    results = {}

remaining = [a for a in sorted_wallets if a not in results]
print(f"Total: {len(sorted_wallets)}, Done: {len(results)}, Remaining: {len(remaining)}", flush=True)

RPC = "https://api.mainnet-beta.solana.com"

# Test first 5 quickly
for i, addr in enumerate(remaining):
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
            "params": [addr, {"encoding": "base64"}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            if "error" in d:
                results[addr] = None
            else:
                v = d.get("result", {}).get("value")
                results[addr] = v is not None
    except Exception as e:
        results[addr] = None
    
    if (i + 1) % 50 == 0:
        OUT.write_text(json.dumps(results))
        exists = sum(1 for v in results.values() if v is True)
        phantom = sum(1 for v in results.values() if v is False)
        err = sum(1 for v in results.values() if v is None)
        print(f"[{i+1}/{len(remaining)}] {exists} exist, {phantom} phantom, {err} err", flush=True)
        sys.stdout.flush()
    
    time.sleep(0.05)

OUT.write_text(json.dumps(results))
exists = sum(1 for v in results.values() if v is True)
phantom = sum(1 for v in results.values() if v is False)
err = sum(1 for v in results.values() if v is None)
print(f"\nDONE: {len(results)}/{len(sorted_wallets)}")
print(f"  EXIST: {exists}")
print(f"  PHANTOM: {phantom}")
print(f"  ERR: {err}")
