#!/usr/bin/env python3
"""Verify all 873 wallets with portfolio stats."""
import json, time, subprocess, sys
from pathlib import Path

TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
VERIF_OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_verified_all.json")

wallet_pnl = {w: sum(t["pnl_sol"] for t in ts) for w, ts in TRADES.items()}

# Load existing
if VERIF_OUT.exists():
    verified = json.load(open(VERIF_OUT))
else:
    verified = {}

# Sort by PnL desc — highest claimed winners first
sorted_wallets = sorted(wallet_pnl.keys(), key=lambda w: wallet_pnl[w], reverse=True)

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"

total = len(sorted_wallets)
print(f"Total: {total}, already verified: {len(verified)}")

for i, addr in enumerate(sorted_wallets):
    if addr in verified:
        continue
    
    r = subprocess.run([GMGN, "portfolio", "stats", "--chain", "sol",
                        "--wallet", addr, "--period", "30d", "--raw"],
                       capture_output=True, text=True, timeout=15)
    
    if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
        # Save and wait
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"\nRATE LIMIT at {i+1}/{total} - saved {len(verified)}")
        sys.exit(0)
    
    try:
        d = json.loads(r.stdout)
        buy = d.get("buy", 0)
        sell = d.get("sell", 0)
        realized = float(d.get("realized_profit", 0) or 0)
        last_ts = d.get("last_timestamp", 0)
        tokens_traded = d.get("pnl_stat", {}).get("token_num", 0)
        
        verified[addr] = {
            "realized_profit_30d": realized,
            "buy_30d": buy,
            "sell_30d": sell,
            "tokens_traded_30d": tokens_traded,
            "last_timestamp": last_ts,
            "is_verified": (buy + sell) > 0 and last_ts > 0 and realized > 0,
        }
    except Exception:
        continue
    
    if (i + 1) % 50 == 0:
        real = sum(1 for v in verified.values() if v["is_verified"])
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"[{i+1}/{total}] {real} real, {len(verified)-real} suspicious", flush=True)
    
    time.sleep(0.4)

VERIF_OUT.write_text(json.dumps(verified))
real = sum(1 for v in verified.values() if v["is_verified"])
fake = len(verified) - real
print(f"\nDONE: {len(verified)} checked ({real} real, {fake} suspicious)")
