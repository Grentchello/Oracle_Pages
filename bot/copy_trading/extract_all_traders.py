#!/usr/bin/env python3
"""
Extract ALL winning wallet-trader pairs from our 62 quality tokens.
Output: all_wallet_trades.json with 903+ wallets
"""
import json, time, subprocess, sys
from pathlib import Path

TOKENS = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/tokens_100.json"))
OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json")
DONE = Path("/opt/data/hermes_work/bot/copy_trading/cache/all_traders_done.txt")

done = set(DONE.read_text().splitlines()) if DONE.exists() else set()
trades = json.load(open(OUT)) if OUT.exists() else {}

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"

remaining = [t for t in TOKENS if t["address"] not in done]
print(f"Total tokens: {len(TOKENS)}")
print(f"Already fetched: {len(done)}")
print(f"Remaining: {len(remaining)}", flush=True)

for i, t in enumerate(remaining):
    addr = t["address"]
    sym = t.get("symbol", "?")
    
    # Fetch traders (limit 80 per token)
    success = False
    for attempt in range(3):
        r = subprocess.run([GMGN, "token", "traders", "--chain", "sol",
                            "--address", addr, "--limit", "80", "--raw"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and "RATE_LIMIT" not in r.stdout:
            try:
                d = json.loads(r.stdout).get("list", [])
                added = 0
                for tr in d:
                    w = tr.get("account_address")
                    pnl = float(tr.get("realized_profit", 0) or 0)
                    if not w or pnl <= 0:
                        continue
                    if w not in trades:
                        trades[w] = []
                    trades[w].append({
                        "token": sym,
                        "token_address": addr,
                        "pnl_sol": pnl,
                        "pnl_pct": float(tr.get("realized_pnl", 0) or 0),
                        "buy": tr.get("buy", 0),
                        "sell": tr.get("sell", 0),
                    })
                    added += 1
                success = True
                print(f"[{i+1}/{len(remaining)}] {sym:10s} +{added} wallets (total: {len(trades)})", flush=True)
                break
            except Exception as e:
                print(f"  [PARSE ERR] {e}", flush=True)
                continue
        if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
            print("  RATE LIMIT 60s", flush=True)
            time.sleep(60)
    
    if not success:
        print(f"[{i+1}/{len(remaining)}] {sym} SKIP", flush=True)
    
    # Save progress
    with open(DONE, "a") as f:
        f.write(addr + "\n")
    done.add(addr)
    OUT.write_text(json.dumps(trades))
    
    # Progress every 5
    if (i + 1) % 5 == 0:
        OUT.write_text(json.dumps(trades))
    
    time.sleep(1.5)

OUT.write_text(json.dumps(trades))
print(f"\nDONE: {len(trades)} unique wallets")
