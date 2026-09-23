#!/usr/bin/env python3
"""
Find active copy-trade targets — many more than before.
Strategy:
1. Pull large pool of recent Pump.fun tokens
2. Get fresh_wallet tagged top traders from each
3. Filter: funded + ≥48h hold + profitable + ≤2 SOL avg buy + ACTIVE in last 24h
4. Take top 30 by score
"""
import subprocess, json, time, urllib.request, datetime
from pathlib import Path

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"
RPC = "https://api.mainnet-beta.solana.com"
HISTORY = Path("/opt/data/hermes_work/bot/copy_trading/cache/scanned_tokens_history.json")

# Load history — exclude already-scanned tokens
history = json.loads(HISTORY.read_text())
seen_addrs = set(history["scanned_addresses"])
print(f"History: {len(seen_addrs)} tokens already scanned", flush=True)

# Step 1: Get NEW tokens (broad search)
new_tokens = []
fetched = set()
for sortby in ["created_timestamp", "volume_24h", "swaps_24h", "smart_degen_count", "renowned_count", "holder_count"]:
    for direction in ["desc"]:
        for preset in ["smart-money", "safe"]:
            cmd = [GMGN, "market", "trenches", "--chain", "sol",
                   "--type", "completed",
                   "--filter-preset", preset,
                   "--sort-by", sortby,
                   "--direction", direction,
                   "--limit", "80", "--raw"]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if r.returncode != 0 or "RATE_LIMIT" in r.stdout:
                    if "RATE_LIMIT" in r.stdout: time.sleep(60)
                    continue
                d = json.loads(r.stdout)
                added = 0
                for t in d.get("completed", []):
                    a = t.get("address")
                    if a and a not in fetched and a not in seen_addrs:
                        fetched.add(a)
                        new_tokens.append({
                            "address": a,
                            "symbol": t.get("symbol"),
                            "mc": t.get("market_cap"),
                            "vol24h": t.get("volume_24h"),
                            "smart_degens": t.get("smart_degen_count"),
                        })
                        added += 1
                if added > 0:
                    print(f"  +{added} new tokens", flush=True)
            except Exception as e:
                pass
            time.sleep(1.5)

print(f"\nTotal new tokens: {len(new_tokens)}", flush=True)
print(f"Fetching fresh traders for each...", flush=True)

# Step 2: Get fresh traders per token
all_traders = {}
for i, t in enumerate(new_tokens):
    addr = t["address"]
    success = False
    for attempt in range(2):
        r = subprocess.run([GMGN, "token", "traders", "--chain", "sol",
                            "--address", addr, "--tag", "fresh_wallet",
                            "--limit", "100", "--order-by", "profit",
                            "--direction", "desc", "--raw"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and "RATE_LIMIT" not in r.stdout:
            try:
                d = json.loads(r.stdout)
                all_traders[addr] = {
                    "symbol": t["symbol"], "traders": d.get("list", [])
                }
                success = True
                break
            except:
                pass
        if "RATE_LIMIT" in r.stdout:
            time.sleep(60)
    if not success:
        all_traders[addr] = {"error": "rate", "symbol": t["symbol"]}
    
    if (i + 1) % 10 == 0:
        unique = set()
        for v in all_traders.values():
            if isinstance(v.get("traders"), list):
                for tt in v["traders"]:
                    unique.add(tt.get("account_address"))
        print(f"  [{i+1}/{len(new_tokens)}] {len(unique)} unique traders", flush=True)
    time.sleep(1.5)

# Save raw
Path("/opt/data/hermes_work/bot/copy_trading/cache/fresh_traders_active_scan.json").write_text(
    json.dumps(all_traders, indent=2)
)
print(f"\nSaved {len(all_traders)} tokens of fresh traders")

# Update history
newly_added = set(t["address"] for t in new_tokens)
seen_addrs.update(newly_added)
history["scanned_addresses"] = sorted(seen_addrs)
history["last_scan"] = datetime.datetime.utcnow().isoformat() + "Z"
history["scan_count"] = history.get("scan_count", 0) + 1
HISTORY.write_text(json.dumps(history, indent=2))
print(f"History updated: {history['scan_count']} scans, {len(seen_addrs)} addresses tracked")
