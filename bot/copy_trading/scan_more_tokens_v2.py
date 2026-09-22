#!/usr/bin/env python3
"""Expand token list to 500+ migrated tokens by varying ALL parameters."""
import subprocess, json, time
from pathlib import Path

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"
OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/migrated_tokens_xl.json")

existing = []
if OUT.exists():
    existing = json.load(open(OUT))
existing_addr = set(t["address"] for t in existing)

new = []
seen = set(existing_addr)

# Try MANY combinations
combos = []
for sortby in ["created_timestamp", "volume_24h", "swaps_24h", "usd_market_cap",
                 "smart_degen_count", "renowned_count", "holder_count",
                 "net_buy_24h", "buys_24h"]:
    for direction in ["desc", "asc"]:
        combos.append({"sort_by": sortby, "direction": direction})

presets = ["smart-money", "safe", "strict"]
filters = [
    {},
    {"min_volume_24h": 5000},
    {"min_volume_24h": 50000},
    {"min_volume_24h": 200, "min_swaps_24h": 50},  # lenient
    {"min_volume_24h": 5000, "min_net_buy_24h": 1000},
    {"min_volume_24h": 5000, "min_swaps_24h": 500, "min_holders": 10},
]

# Get 80 tokens per call to maximize
for combo in combos[:20]:  # cap to avoid rate limits
    for preset in presets[:2]:
        for f in filters:
            cmd = [GMGN, "market", "trenches", "--chain", "sol",
                   "--type", "completed",
                   "--filter-preset", preset,
                   "--sort-by", combo["sort_by"],
                   "--direction", combo["direction"],
                   "--limit", "80", "--raw"]
            for k, v in f.items():
                cmd.extend([f"--{k}", str(v)])
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
                        added += 1
                if added > 0:
                    print(f"  {preset}/{combo['sort_by'][:15]}/{combo['direction']}/{len(f)}: +{added}", flush=True)
            except Exception as e:
                print(f"  err: {e}", flush=True)
            time.sleep(1.5)

combined = existing + new
OUT.write_text(json.dumps(combined, indent=2))
print(f"\nTotal: {len(combined)} tokens (added {len(new)})")
