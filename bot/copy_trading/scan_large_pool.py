#!/usr/bin/env python3
"""
Scan a much bigger pool of migrated tokens to find real active traders.
Strategy:
1. Pull 1000+ migrated tokens (multiple sort orders, presets)
2. For each token, get top 50 traders (no fresh tag - just by profit)
3. Aggregate unique wallets
4. Save raw to /cache
"""
import subprocess, json, time
from pathlib import Path

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"
HISTORY = Path("/opt/data/hermes_work/bot/copy_trading/cache/scanned_tokens_history.json")
OUTPUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/large_token_pool.json")

# Load history
history = json.loads(HISTORY.read_text())
seen = set(history["scanned_addresses"])
print(f"History: {len(seen)} tokens already in history")

# Get more tokens - aggressive
all_tokens = []
fetched = set(seen)

# Multiple sort orders, presets, directions - aim for 1000+ unique tokens
combos = []
for sortby in ["created_timestamp", "volume_24h", "swaps_24h", "smart_degen_count", 
                "renowned_count", "holder_count", "net_buy_24h"]:
    for direction in ["desc"]:
        for preset in ["smart-money", "safe", "strict"]:
            combos.append({"sort_by": sortby, "direction": direction, "preset": preset})

print(f"Total combos to try: {len(combos)}")
print(f"Target: 500-1000 unique NEW tokens")

for i, combo in enumerate(combos):
    cmd = [GMGN, "market", "trenches", "--chain", "sol",
           "--type", "completed",
           "--filter-preset", combo["preset"],
           "--sort-by", combo["sort_by"],
           "--direction", combo["direction"],
           "--limit", "80", "--raw"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0 or "RATE_LIMIT" in r.stdout:
            if "RATE_LIMIT" in r.stdout:
                time.sleep(60)
            continue
        d = json.loads(r.stdout)
        added = 0
        for t in d.get("completed", []):
            a = t.get("address")
            if a and a not in fetched:
                fetched.add(a)
                all_tokens.append({
                    "address": a,
                    "symbol": t.get("symbol"),
                    "mc": t.get("market_cap"),
                    "vol24h": t.get("volume_24h"),
                    "smart_degens": t.get("smart_degen_count"),
                    "bot_degens": t.get("bot_degen_count"),
                })
                added += 1
        if added > 0:
            print(f"  [{i+1}] +{added} new (total: {len(all_tokens)})", flush=True)
    except Exception as e:
        pass
    time.sleep(1.5)

print(f"\nTotal new tokens: {len(all_tokens)}")

# Combine with existing
OUTPUT.write_text(json.dumps(all_tokens, indent=2))
print(f"Saved to {OUTPUT}")

# Update history
new_addrs = set(t["address"] for t in all_tokens)
seen.update(new_addrs)
history["scanned_addresses"] = sorted(seen)
history["last_scan"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
history["scan_count"] = history.get("scan_count", 0) + 1
HISTORY.write_text(json.dumps(history, indent=2))
print(f"History: {len(seen)} total addresses tracked")
