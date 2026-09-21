#!/usr/bin/env python3
"""Re-verify wallets with corrected criteria (last_ts > 0 or tokens > 0)."""
import json, time, subprocess, sys
from pathlib import Path

TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
VERIF_OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_verified_all_v2.json")

wallet_pnl = {w: sum(t["pnl_sol"] for t in ts) for w, ts in TRADES.items()}

if VERIF_OUT.exists():
    verified = json.load(open(VERIF_OUT))
else:
    verified = {}

# Reset — start fresh with new criteria
verified = {}

sorted_wallets = sorted(wallet_pnl.keys(), key=lambda w: wallet_pnl[w], reverse=True)
total = len(sorted_wallets)
print(f"Total: {total}, will verify: {total}")
print("Criteria: last_timestamp > 0 OR tokens_traded > 0")

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"

for i, addr in enumerate(sorted_wallets):
    if addr in verified:
        continue
    
    r = subprocess.run([GMGN, "portfolio", "stats", "--chain", "sol",
                        "--wallet", addr, "--period", "30d", "--raw"],
                       capture_output=True, text=True, timeout=15)
    
    if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"\nRATE LIMIT at {i+1}/{total} - saved {len(verified)}")
        sys.exit(0)
    
    try:
        d = json.loads(r.stdout)
        last_ts = d.get("last_timestamp", 0)
        tokens_traded = d.get("pnl_stat", {}).get("token_num", 0)
        realized = float(d.get("realized_profit", 0) or 0)
        buy = d.get("buy", 0)
        sell = d.get("sell", 0)
        
        # REAL activity indicator
        is_real = last_ts > 0 and tokens_traded > 0
        # STRICT: positive PnL too
        has_pnl = is_real and realized > 0
        
        verified[addr] = {
            "last_timestamp": last_ts,
            "tokens_traded_30d": tokens_traded,
            "realized_profit_30d": realized,
            "buy_30d": buy,
            "sell_30d": sell,
            "is_verified": is_real,
            "has_profit": has_pnl,
        }
    except Exception:
        continue
    
    if (i + 1) % 50 == 0:
        real = sum(1 for v in verified.values() if v["is_verified"])
        profit = sum(1 for v in verified.values() if v["has_profit"])
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"[{i+1}/{total}] {real} have activity, {profit} profitable", flush=True)
    
    time.sleep(2.5)  # SLOWER to avoid rate limit (24 req/min)

VERIF_OUT.write_text(json.dumps(verified))
real = sum(1 for v in verified.values() if v["is_verified"])
profit = sum(1 for v in verified.values() if v["has_profit"])
print(f"\nDONE: {len(verified)} checked ({real} active, {profit} profitable)")
