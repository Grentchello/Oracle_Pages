#!/usr/bin/env python3
"""Scan many more tokens with varied parameters."""
import subprocess, json, time
from pathlib import Path

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"
OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/migrated_tokens_large.json")

existing = []
if OUT.exists():
    existing = json.load(open(OUT))
existing_addr = set(t["address"] for t in existing)

new = []
seen = set(existing_addr)

# Try MANY combos to maximize token coverage
combos = [
    # different sort orders
    {"sort_by": "created_timestamp", "direction": "desc", "label": "newest"},
    {"sort_by": "volume_24h", "direction": "desc", "label": "vol24h"},
    {"sort_by": "swaps_24h", "direction": "desc", "label": "swaps24h"},
    {"sort_by": "usd_market_cap", "direction": "desc", "label": "mc"},
    {"sort_by": "smart_degen_count", "direction": "desc", "label": "smartdegen"},
    {"sort_by": "renowned_count", "direction": "desc", "label": "renowned"},
    {"sort_by": "holder_count", "direction": "desc", "label": "holders"},
]
presets = ["smart-money", "safe", "strict"]
filters = [
    {"min_volume_24h": 5000, "min_net_buy_24h": 1000, "min_swaps_24h": 500},
    {"min_volume_24h": 50000, "min_net_buy_24h": 10000, "min_swaps_24h": 5000},
    {"min_volume_24h": 1000, "min_swaps_24h": 100},  # more lenient
]

for combo in combos:
    for preset in presets:
        for f in filters:
            try:
                cmd = [GMGN, "market", "trenches", "--chain", "sol",
                       "--type", "completed",
                       "--filter-preset", preset,
                       "--sort-by", combo["sort_by"],
                       "--direction", combo["direction"],
                       "--limit", "80", "--raw"]
                if "min_volume_24h" in f:
                    cmd.extend(["--min-volume-24h", str(f["min_volume_24h"])])
                if "min_net_buy_24h" in f:
                    cmd.extend(["--min-net-buy-24h", str(f["min_net_buy_24h"])])
                if "min_swaps_24h" in f:
                    cmd.extend(["--min-swaps-24h", str(f["min_swaps_24h"])])
                
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if r.returncode != 0 or "RATE_LIMIT" in r.stdout:
                    if "RATE_LIMIT" in r.stdout:
                        time.sleep(60)
                    continue
                
                d = json.loads(r.stdout)
                for t in d.get("completed", []):
                    a = t.get("address")
                    if a and a not in seen:
                        seen.add(a)
                        new.append({
                            "address": a,
                            "symbol": t.get("symbol"),
                            "mc": t.get("market_cap"),
                            "vol24h": t.get("volume_24h"),
                            "swaps24h": t.get("swaps_24h"),
                            "holders": t.get("holder_count"),
                            "smart_degens": t.get("smart_degen_count"),
                            "bot_degens": t.get("bot_degen_count"),
                            "created": t.get("created_timestamp"),
                        })
            except Exception as e:
                print(f"err: {e}", flush=True)
            
            time.sleep(1.5)

combined = existing + new
OUT.write_text(json.dumps(combined, indent=2))
print(f"\nTotal migrated tokens: {len(combined)} (added {len(new)})")
