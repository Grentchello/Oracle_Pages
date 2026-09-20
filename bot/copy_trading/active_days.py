#!/usr/bin/env python3
"""For each of 55 target wallets, count DISTINCT active trading days in last 30d."""
import json, time, urllib.request
from pathlib import Path

TARGET = json.load(open("/opt/data/hermes_work/bot/copy_trading/target_wallets.json"))
wallets = TARGET["wallets"]

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_active_days.json")
if OUT.exists():
    results = json.load(open(OUT))
else:
    results = {}

RPC = "https://api.mainnet-beta.solana.com"

remaining = [w for w in wallets if w["wallet"] not in results]
print(f"Total target: {len(wallets)}, need to check: {len(remaining)}", flush=True)

for i, w in enumerate(remaining):
    addr = w["wallet"]
    try:
        # Get signatures over the last 30 days - need to use before/until params
        # to paginate through history. For simplicity, just get the most recent 200 sigs.
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [addr, {"limit": 1000}]  # Get all available
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read())
            sigs = d.get("result", [])
        
        if not sigs:
            results[addr] = {"active_days_30d": 0, "total_txs": 0}
            continue
        
        # Count unique days in last 30 days
        import datetime
        now = int(time.time())
        thirty_days_ago = now - 30 * 86400
        
        active_days = set()
        for s in sigs:
            bt = s.get("blockTime", 0)
            if bt >= thirty_days_ago:
                day = datetime.datetime.fromtimestamp(bt).strftime('%Y-%m-%d')
                active_days.add(day)
        
        results[addr] = {
            "active_days_30d": len(active_days),
            "active_days_list": sorted(active_days),
            "total_txs_30d": sum(1 for s in sigs if s.get("blockTime", 0) >= thirty_days_ago),
            "last_tx_time": sigs[0].get("blockTime", 0) if sigs else 0,
        }
    except Exception as e:
        results[addr] = {"error": str(e)[:200]}
    
    if (i + 1) % 10 == 0:
        OUT.write_text(json.dumps(results))
        qualifying = sum(1 for v in results.values() if v.get("active_days_30d", 0) >= 15)
        print(f"[{i+1}/{len(remaining)}] {qualifying} qualifying (15+ days active)", flush=True)
    
    time.sleep(1.0)  # Rate protection

OUT.write_text(json.dumps(results))
qualifying = [r for r in results.values() if r.get("active_days_30d", 0) >= 15]
print(f"\nFINAL: {len(qualifying)}/{len(remaining)} wallets active 15+ days in 30d")
