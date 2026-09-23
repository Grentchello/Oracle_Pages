#!/usr/bin/env python3
"""For each token in large pool, get top traders by profit."""
import subprocess, json, time, sys
from pathlib import Path

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"
TOKENS_FILE = Path("/opt/data/hermes_work/bot/copy_trading/cache/large_token_pool.json")
OUTPUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/large_traders.json")

tokens = json.loads(TOKENS_FILE.read_text())
print(f"Tokens: {len(tokens)}", flush=True)

# Aggregate per-wallet data
wallet_data = {}
processed = 0
errors = 0

for i, t in enumerate(tokens):
    addr = t["address"]
    sym = t.get("symbol", "?")
    
    # Try multiple order-bys to get more diverse results
    for order_by in ["profit", "buy_volume_cur"]:
        success = False
        for attempt in range(2):
            r = subprocess.run([GMGN, "token", "traders", "--chain", "sol",
                                "--address", addr, "--limit", "50",
                                "--order-by", order_by,
                                "--direction", "desc", "--raw"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and "RATE_LIMIT" not in r.stdout:
                try:
                    d = json.loads(r.stdout)
                    traders = d.get("list", [])
                    for tr in traders:
                        w = tr.get("account_address")
                        if not w: continue
                        pnl = float(tr.get("realized_profit", 0) or 0)
                        buy_vol = float(tr.get("buy_volume_cur", 0) or 0)
                        sell_vol = float(tr.get("sell_volume_cur", 0) or 0)
                        buy_txs = int(tr.get("buy_tx_count_cur", 0) or 0)
                        sell_txs = int(tr.get("sell_tx_count_cur", 0) or 0)
                        created = int(tr.get("created_at", 0) or 0)
                        nv = tr.get("native_transfer", {}) or {}
                        
                        if w not in wallet_data:
                            wallet_data[w] = {
                                "pnl": 0, "buy_vol": 0, "sell_vol": 0,
                                "buy_txs": 0, "sell_txs": 0,
                                "funding": "", "funding_ts": 0, "created": 0,
                                "tokens": set(),
                            }
                        wallet_data[w]["pnl"] += pnl
                        wallet_data[w]["buy_vol"] += buy_vol
                        wallet_data[w]["sell_vol"] += sell_vol
                        wallet_data[w]["buy_txs"] += buy_txs
                        wallet_data[w]["sell_txs"] += sell_txs
                        wallet_data[w]["tokens"].add(sym)
                        if not wallet_data[w]["funding"] and nv.get("name"):
                            wallet_data[w]["funding"] = nv["name"]
                            wallet_data[w]["funding_ts"] = int(nv.get("timestamp", 0))
                        if created and (not wallet_data[w]["created"] or created < wallet_data[w]["created"]):
                            wallet_data[w]["created"] = created
                    success = True
                    break
                except Exception:
                    pass
            if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
                time.sleep(60)
            else:
                errors += 1
                break
        
        if not success:
            errors += 1
    
    processed += 1
    if processed % 10 == 0:
        # Save intermediate
        save_data = {k: {**v, "tokens": list(v["tokens"])} for k, v in wallet_data.items()}
        OUTPUT.write_text(json.dumps(save_data, indent=2))
        print(f"  [{processed}/{len(tokens)}] {len(wallet_data)} unique wallets, {errors} errors", flush=True)
    time.sleep(1.0)

# Final save
save_data = {k: {**v, "tokens": list(v["tokens"])} for k, v in wallet_data.items()}
OUTPUT.write_text(json.dumps(save_data, indent=2))
print(f"\nDONE: {len(wallet_data)} unique wallets, {errors} errors", flush=True)
