#!/usr/bin/env python3
"""Scan migrated/graduated tokens for fresh traders."""
import subprocess, json, time, sys
from pathlib import Path

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"

# Use pump_mayhem + Pump.fun launchpads to focus on actual migrated tokens
# Also use sort-by recent so we get fresh migrated ones
all_tokens = []
seen = set()

# Get multiple batches with different sort orders
for sortby in ["created_timestamp", "volume_24h", "swaps_24h", "smart_degen_count"]:
    for ttype in ["completed"]:  # only completed = migrated/graduated
        for preset in ["smart-money", "safe"]:  # alternating to avoid overlap
            try:
                r = subprocess.run([GMGN, "market", "trenches", "--chain", "sol",
                                    "--type", ttype,
                                    "--filter-preset", preset,
                                    "--sort-by", sortby,
                                    "--min-volume-24h", "5000",
                                    "--min-net-buy-24h", "1000",
                                    "--limit", "80", "--raw"],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode != 0:
                    continue
                if "RATE_LIMIT" in r.stdout:
                    print(f"  RATE LIMIT (sleep 60s)...", flush=True)
                    time.sleep(60)
                    continue
                    
                d = json.loads(r.stdout)
                batch = d.get(ttype, [])
                added = 0
                for t in batch:
                    a = t.get("address")
                    if a and a not in seen:
                        seen.add(a)
                        all_tokens.append(t)
                        added += 1
                print(f"  {preset}/{sortby}/{ttype}: got {len(batch)}, +{added} new", flush=True)
            except Exception as e:
                print(f"  err: {e}", flush=True)
            
            time.sleep(2.0)  # gentle pacing

# Filter: must have decent migration metrics
filtered = []
for t in all_tokens:
    mc = t.get("market_cap", 0)
    vol = t.get("volume_24h", 0)
    swaps = t.get("swaps_24h", 0)
    holders = t.get("holder_count", 0)
    
    # Migrated tokens should have:
    # - Market cap > some threshold
    # - Decent volume
    # - Some holder count
    if mc < 10000 or vol < 5000:
        continue
    filtered.append(t)

print(f"\nTotal tokens: {len(all_tokens)}, after quality filter: {len(filtered)}")

# Save
Path("/opt/data/hermes_work/bot/copy_trading/cache/migrated_tokens.json").write_text(
    json.dumps([{
        "address": t["address"],
        "symbol": t.get("symbol"),
        "mc": t.get("market_cap"),
        "vol24h": t.get("volume_24h"),
        "swaps24h": t.get("swaps_24h"),
        "holders": t.get("holder_count"),
        "smart_degens": t.get("smart_degen_count"),
        "bot_degens": t.get("bot_degen_count"),
        "created": t.get("created_timestamp"),
    } for t in filtered], indent=2)
)
print(f"Saved {len(filtered)} migrated tokens")
