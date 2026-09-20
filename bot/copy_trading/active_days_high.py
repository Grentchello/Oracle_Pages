#!/usr/bin/env python3
"""Check active_days for the 27 high-tx (50+) wallets."""
import json, time, urllib.request, datetime
from pathlib import Path

TX = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count.json"))
TX2 = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count_v2.json"))
all_tx = {**TX, **TX2}

target = [a for a, v in all_tx.items() 
          if isinstance(v.get("recent_txs_30d"), int) and v["recent_txs_30d"] >= 50]
print(f"Wallets to check: {len(target)}", flush=True)

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_active_days_high.json")
if OUT.exists():
    results = json.load(open(OUT))
else:
    results = {}

RPC = "https://api.mainnet-beta.solana.com"

remaining = [a for a in target if a not in results]
print(f"Remaining: {len(remaining)}", flush=True)

for i, addr in enumerate(remaining):
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [addr, {"limit": 1000}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            d = json.loads(resp.read())
            sigs = d.get("result", [])
        
        if not sigs:
            results[addr] = {"active_days_30d": 0}
            continue
        
        now = int(time.time())
        thirty = now - 30 * 86400
        
        active_days = set()
        total_30d = 0
        for s in sigs:
            bt = s.get("blockTime", 0)
            if bt >= thirty:
                total_30d += 1
                day = datetime.datetime.fromtimestamp(bt).strftime('%Y-%m-%d')
                active_days.add(day)
        
        results[addr] = {
            "active_days_30d": len(active_days),
            "total_txs_30d": total_30d,
            "recent_txs_30d": all_tx[addr].get("recent_txs_30d"),
        }
    except Exception as e:
        results[addr] = {"error": str(e)[:200]}
    
    if (i + 1) % 5 == 0:
        OUT.write_text(json.dumps(results))
        qual = sum(1 for v in results.values() 
                   if isinstance(v.get("active_days_30d"), int) and v.get("active_days_30d", 0) >= 15)
        print(f"[{i+1}/{len(remaining)}] {qual} qualifying (15+ days active)", flush=True)
    
    time.sleep(1.5)

OUT.write_text(json.dumps(results))
qual = sum(1 for v in results.values() 
           if isinstance(v.get("active_days_30d"), int) and v.get("active_days_30d", 0) >= 15)
print(f"\nDONE: {len(results)} checked")
print(f"Qualifying (15+ days): {qual}")
