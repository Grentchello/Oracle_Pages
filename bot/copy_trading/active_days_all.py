#!/usr/bin/env python3
"""Check active_days for ALL 753 real wallets."""
import json, time, urllib.request, datetime
from pathlib import Path

RPC_CHECK = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_rpc_seq.json"))

real = [a for a, v in RPC_CHECK.items() if v is True]
print(f"Real wallets: {len(real)}", flush=True)

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_active_days_all.json")
if OUT.exists():
    results = json.load(open(OUT))
else:
    results = {}

RPC = "https://api.mainnet-beta.solana.com"
remaining = [a for a in real if a not in results]
print(f"Remaining: {len(remaining)}", flush=True)

# Track progress with detailed distribution
for i, addr in enumerate(remaining):
    try:
        # Use strict timeout
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [addr, {"limit": 1000}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read())
            sigs = d.get("result", [])
        
        if not sigs:
            results[addr] = {"active_days_30d": 0, "total_txs_30d": 0}
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
        }
    except Exception as e:
        results[addr] = {"error": str(e)[:100]}
    
    if (i + 1) % 25 == 0:
        OUT.write_text(json.dumps(results))
        # Distribution
        from collections import Counter
        days = [v.get("active_days_30d", 0) for v in results.values() 
                if isinstance(v.get("active_days_30d"), int)]
        buckets = Counter()
        for d in days:
            if d >= 15: buckets["15+"] += 1
            elif d >= 5: buckets["5-14"] += 1
            elif d >= 1: buckets["1-4"] += 1
            else: buckets["0"] += 1
        print(f"[{i+1}/{len(remaining)}] {buckets['15+']} 15+day, {buckets['5-14']} 5-14, {buckets['1-4']} 1-4, {buckets['0']} 0", flush=True)
    
    time.sleep(0.5)

OUT.write_text(json.dumps(results))
from collections import Counter
days = [v.get("active_days_30d", 0) for v in results.values() 
        if isinstance(v.get("active_days_30d"), int)]
buckets = Counter()
for d in days:
    if d >= 15: buckets["15+"] += 1
    elif d >= 5: buckets["5-14"] += 1
    elif d >= 1: buckets["1-4"] += 1
    else: buckets["0"] += 1
print(f"\nFINAL: {len(results)} checked")
print(f"  15+ days: {buckets['15+']}")
print(f"  5-14 days: {buckets['5-14']}")
print(f"  1-4 days: {buckets['1-4']}")
print(f"  0 days: {buckets['0']}")
