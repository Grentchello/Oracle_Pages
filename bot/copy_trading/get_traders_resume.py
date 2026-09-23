#!/usr/bin/env python3
"""Get top traders from large pool, with resume + rate-limit handling."""
import subprocess, json, time
from pathlib import Path

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"
TOKENS_FILE = Path("/opt/data/hermes_work/bot/copy_trading/cache/large_token_pool.json")
OUTPUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/large_traders_v2.json")

tokens = json.loads(TOKENS_FILE.read_text())
print(f"Tokens: {len(tokens)}", flush=True)

# Resume from existing
if OUTPUT.exists():
    wallet_data = json.loads(OUTPUT.read_text())
    # Convert tokens lists back to sets
    wallet_data = {k: {**v, "tokens": set(v["tokens"])} for k, v in wallet_data.items()}
    print(f"Resumed with {len(wallet_data)} wallets", flush=True)
else:
    wallet_data = {}

# Track which tokens we've fully processed
TOKEN_LOG = Path("/opt/data/hermes_work/bot/copy_trading/cache/tokens_processed.log")
done = set()
if TOKEN_LOG.exists():
    done = set(TOKEN_LOG.read_text().splitlines())
print(f"Tokens already processed: {len(done)}", flush=True)

errors = 0
for i, t in enumerate(tokens):
    addr = t["address"]
    if addr in done: continue
    sym = t.get("symbol", "?")
    
    # Try multiple order-bys
    for order_by in ["profit", "buy_volume_cur"]:
        success = False
        for attempt in range(2):
            r = subprocess.run([GMGN, "token", "traders", "--chain", "sol",
                                "--address", addr, "--limit", "50",
                                "--order-by", order_by,
                                "--direction", "desc", "--raw"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and "RATE_LIMIT" not in r.stdout and "429" not in r.stdout:
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
                print(f"  ⚠️ Rate limited, sleeping 90s", flush=True)
                time.sleep(90)
            else:
                break
        
        if not success:
            errors += 1
    
    # Mark token done
    with open(TOKEN_LOG, "a") as f:
        f.write(addr + "\n")
    done.add(addr)
    
    # Save progress every 5
    if (i + 1) % 5 == 0:
        save_data = {k: {**v, "tokens": list(v["tokens"])} for k, v in wallet_data.items()}
        OUTPUT.write_text(json.dumps(save_data, indent=2))
        print(f"  [{i+1}/{len(tokens)}] {len(wallet_data)} wallets, {errors} err", flush=True)
    
    time.sleep(2.5)  # Slow to avoid rate limits

# Final save
save_data = {k: {**v, "tokens": list(v["tokens"])} for k, v in wallet_data.items()}
OUTPUT.write_text(json.dumps(save_data, indent=2))
print(f"\nDONE: {len(wallet_data)} unique wallets", flush=True)
