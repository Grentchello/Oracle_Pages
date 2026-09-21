#!/usr/bin/env python3
"""For each of 260 migrated tokens, get fresh_wallet tagged traders."""
import subprocess, json, time, sys
from pathlib import Path

TOKENS = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/migrated_tokens_large.json"))
GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/fresh_wallet_traders_full.json")
if OUT.exists():
    fresh_data = json.load(open(OUT))
else:
    fresh_data = {}

target = [t for t in TOKENS if t["address"] not in fresh_data]
print(f"Tokens: {len(TOKENS)}, already done: {len(fresh_data)}, remaining: {len(target)}", flush=True)

for i, t in enumerate(target):
    addr = t["address"]
    sym = t.get("symbol", "?")
    
    success = False
    for attempt in range(3):
        r = subprocess.run([GMGN, "token", "traders", "--chain", "sol",
                            "--address", addr, "--tag", "fresh_wallet",
                            "--limit", "100", "--order-by", "profit",
                            "--direction", "desc", "--raw"],
                           capture_output=True, text=True, timeout=60)
        
        if r.returncode == 0 and "RATE_LIMIT" not in r.stdout:
            try:
                d = json.loads(r.stdout)
                fresh_data[addr] = {
                    "symbol": sym,
                    "mc": t.get("mc"),
                    "vol24h": t.get("vol24h"),
                    "traders": d.get("list", []),
                }
                success = True
                break
            except Exception:
                pass
        
        if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
            print(f"  RATE LIMIT (60s)...", flush=True)
            time.sleep(60)
            continue
    
    if not success:
        fresh_data[addr] = {"error": "rate limited", "symbol": sym}
    
    if (i + 1) % 10 == 0:
        OUT.write_text(json.dumps(fresh_data))
        total_fresh = sum(len(v.get("traders", [])) for v in fresh_data.values() if isinstance(v, dict) and isinstance(v.get("traders"), list))
        print(f"[{i+1}/{len(target)}] {total_fresh} fresh entries so far", flush=True)
    
    time.sleep(1.5)

OUT.write_text(json.dumps(fresh_data))
total = sum(len(v.get("traders", [])) for v in fresh_data.values() if isinstance(v, dict))
unique = set()
for v in fresh_data.values():
    if isinstance(v, dict) and isinstance(v.get("traders"), list):
        for t in v["traders"]:
            unique.add(t.get("account_address"))
print(f"\nDONE")
print(f"  Tokens scanned: {len(fresh_data)}")
print(f"  Fresh entries: {total}")
print(f"  Unique fresh wallets: {len(unique)}")
