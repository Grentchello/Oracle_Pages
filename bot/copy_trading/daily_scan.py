#!/usr/bin/env python3
"""
Daily copy-trading fresh wallet scanner.
Only scans tokens NOT seen in history → truly new signals every day.
"""
import subprocess, json, time, sys, os
from pathlib import Path
from collections import defaultdict
import datetime

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"

CACHE = Path("/opt/data/hermes_work/bot/copy_trading/cache")
HISTORY = CACHE / "scanned_tokens_history.json"
NEW_TOKENS_FILE = CACHE / "new_tokens_today.json"
NEW_TRADERS_FILE = CACHE / "fresh_wallet_traders_today.json"
DAILY_QUALIFIED = CACHE / "fresh_qualified_today.json"

CACHE.mkdir(parents=True, exist_ok=True)

# Load history
history = json.load(open(HISTORY))
seen_addresses = set(history["scanned_addresses"])
print(f"History: {len(seen_addresses)} tokens already scanned", flush=True)

# Step 1: Get tokens, EXCLUDE seen ones
all_tokens = []
seen_fetch = set()

for sortby in ["created_timestamp", "swaps_24h", "usd_market_cap", "smart_degen_count", "renowned_count"]:
    for direction in ["desc", "asc"]:
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
                    if "RATE_LIMIT" in r.stdout:
                        time.sleep(60)
                    continue
                d = json.loads(r.stdout)
                added = 0
                new_today = 0
                for t in d.get("completed", []):
                    a = t.get("address")
                    if a and a not in seen_fetch:
                        seen_fetch.add(a)
                        is_new = a not in seen_addresses  # NEW relative to history
                        entry = {
                            "address": a,
                            "symbol": t.get("symbol"),
                            "mc": t.get("market_cap"),
                            "vol24h": t.get("volume_24h"),
                            "swaps24h": t.get("swaps_24h"),
                            "holders": t.get("holder_count"),
                            "smart_degens": t.get("smart_degen_count"),
                            "is_new_vs_history": is_new,
                        }
                        all_tokens.append(entry)
                        if is_new: new_today += 1
                        added += 1
                if added > 0:
                    print(f"  {preset[:4]}/{sortby[:10]}/{direction}: +{added} ({new_today} new)", flush=True)
            except Exception as e:
                print(f"  err: {e}", flush=True)
            time.sleep(1.5)

# Stats
truly_new = sum(1 for t in all_tokens if t["is_new_vs_history"])
total_seen = sum(1 for t in all_tokens if not t["is_new_vs_history"])
print(f"\nTotal tokens fetched: {len(all_tokens)} ({truly_new} truly new, {total_seen} already-seen skipped by history though appearing in scans)", flush=True)

if not all_tokens:
    print("No new tokens found today")
    sys.exit(0)

# Save today only the truly new
truly_new_tokens = [t for t in all_tokens if t["is_new_vs_history"]]
NEW_TOKENS_FILE.write_text(json.dumps(truly_new_tokens, indent=2))
print(f"Saved {len(truly_new_tokens)} new tokens to {NEW_TOKENS_FILE}")

# Step 2: Get fresh traders for the NEW tokens only
print(f"\nFetching fresh traders for {len(truly_new_tokens)} new tokens...", flush=True)
fresh_data = {}
# Note: existing NEW_TRADERS_FILE entries are keyed by token address internally
# but the on-disk format nests them in per-token dicts without an address key.
# Since today's tokens are all new (filtered vs history), prior trader data
# is for yesterday's tokens and irrelevant. Start fresh.
if NEW_TRADERS_FILE.exists() and os.environ.get("DAILY_SCAN_KEEP_CACHE") == "1":
    existing = json.load(open(NEW_TRADERS_FILE))
    # Best-effort: rehydrate only entries that actually have an address field
    for entry in existing.get("traders", []):
        if isinstance(entry, dict) and entry.get("address"):
            fresh_data[entry["address"]] = entry

for i, t in enumerate(truly_new_tokens):
    addr = t["address"]
    sym = t["symbol"]
    
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
                fresh_data[addr] = {
                    "symbol": sym,
                    "mc": t["mc"],
                    "vol24h": t["vol24h"],
                    "traders": d.get("list", []),
                }
                success = True
                break
            except:
                pass
        if "RATE_LIMIT" in r.stdout:
            time.sleep(60)
    
    if not success:
        fresh_data[addr] = {"error": "rate", "symbol": sym}
    
    if (i + 1) % 10 == 0:
        NEW_TRADERS_FILE.write_text(json.dumps({"traders": list(fresh_data.values())}))
        unique = set()
        for v in fresh_data.values():
            if isinstance(v.get("traders"), list):
                for tt in v["traders"]:
                    unique.add(tt.get("account_address"))
        print(f"  [{i+1}/{len(truly_new_tokens)}] {len(unique)} unique today", flush=True)
    time.sleep(1.5)

NEW_TRADERS_FILE.write_text(json.dumps({"traders": list(fresh_data.values())}))

# Step 3: Apply YouTube filter
CEX = ["Binance", "MEXC", "Gate.io", "Kucoin", "OKX", "Coinbase", "Bybit", "Bitget"]
wallet_data = defaultdict(lambda: {
    "tokens": [], "total_pnl": 0, "n_wins": 0,
    "total_buy": 0, "total_buy_txs": 0,
    "funding": set(), "created": 0, "is_new": False, "v2_tags": set(),
})

for token_addr, info in fresh_data.items():
    if not isinstance(info, dict) or not isinstance(info.get("traders"), list):
        continue
    for t in info["traders"]:
        w = t.get("account_address")
        if not w: continue
        pnl = float(t.get("realized_profit", 0) or 0)
        bv = float(t.get("buy_volume_cur", 0) or 0)
        bx = int(t.get("buy_tx_count_cur", 0) or 0)
        cr = int(t.get("created_at", 0) or 0)
        nv = t.get("native_transfer", {}) or {}
        v2 = t.get("wallet_tag_v2", "")
        
        wallet_data[w]["total_buy"] += bv
        wallet_data[w]["total_buy_txs"] += bx
        if v2: wallet_data[w]["v2_tags"].add(v2)
        
        if pnl > 0:
            wallet_data[w]["n_wins"] += 1
            wallet_data[w]["tokens"].append({
                "token": info.get("symbol", "?"), "pnl": pnl,
                "buy_vol": bv, "buy_tx": bx,
            })
            wallet_data[w]["total_pnl"] += pnl
        
        if cr and (not wallet_data[w]["created"] or cr < wallet_data[w]["created"]):
            wallet_data[w]["created"] = cr
        if nv.get("name"):
            wallet_data[w]["funding"].add(nv["name"])
        if t.get("is_new"):
            wallet_data[w]["is_new"] = True

now = int(datetime.datetime.now().timestamp())
qualified = []
for w, data in wallet_data.items():
    cex = data["funding"] & set(CEX)
    if not cex: continue
    if data["total_pnl"] <= 0: continue
    if data["total_buy_txs"] == 0: continue
    avg = data["total_buy"] / data["total_buy_txs"]
    if avg > 5: continue
    age = None
    if data["created"]:
        age = (now - data["created"]) / 86400
        if age > 60: continue
    if not (0.5 <= data["total_pnl"] <= 200): continue
    
    score = (data["total_pnl"] * 2 + 
             (10 / max(0.5, age or 30)) * 5 + 
             (10 / max(0.5, avg)) * 2)
    qualified.append({
        "wallet": w,
        "score": score,
        "pnl_sol": data["total_pnl"],
        "n_wins": data["n_wins"],
        "avg_buy_per_trade": avg,
        "funding": list(cex)[0],
        "age_days": age,
        "is_new": data["is_new"],
        "v2_tags": list(data["v2_tags"]),
        "tokens": list(set(t["token"] for t in data["tokens"])),
        "win_details": data["tokens"],
    })

qualified.sort(key=lambda x: x["score"], reverse=True)
DAILY_QUALIFIED.write_text(json.dumps({
    "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    "tokens_scanned_new": len(truly_new_tokens),
    "qualified_wallets": len(qualified),
    "wallets": qualified,
}, indent=2))

# Update history
newly_added = {t["address"] for t in truly_new_tokens}
seen_addresses.update(newly_added)
history["scanned_addresses"] = sorted(seen_addresses)
history["last_scan"] = datetime.datetime.utcnow().isoformat() + "Z"
history["scan_count"] = history.get("scan_count", 0) + 1
HISTORY.write_text(json.dumps(history, indent=2))

print(f"\nDONE")
print(f"  New tokens today: {len(truly_new_tokens)}")
print(f"  Qualified wallets: {len(qualified)}")
print(f"  Total unique wallets in fresh_data: {len(wallet_data)}")
print(f"  History updated: {history['scan_count']} scans, {len(seen_addresses)} addresses tracked")
