#!/usr/bin/env python3
"""Resume verification with on-chain RPC final check."""
import json, time, subprocess, sys, urllib.request
from pathlib import Path

TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
VERIF_OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_verified_all_v2.json")

wallet_pnl = {w: sum(t["pnl_sol"] for t in ts) for w, ts in TRADES.items()}

# Load existing
if VERIF_OUT.exists():
    verified = json.load(open(VERIF_OUT))
else:
    verified = {}

# Sort by PnL desc — top first
sorted_wallets = sorted(wallet_pnl.keys(), key=lambda w: wallet_pnl[w], reverse=True)

remaining = [a for a in sorted_wallets if a not in verified]
print(f"Total: {len(sorted_wallets)}, already verified: {len(verified)}, remaining: {len(remaining)}")

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"
RPC = "https://api.mainnet-beta.solana.com"

def rpc_check(addr):
    """Quick Solana RPC check — does wallet exist?"""
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
            "params": [addr, {"encoding": "base64"}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            d = json.loads(resp.read())
            v = d.get("result", {}).get("value")
            return v is not None  # exists if non-null
    except Exception:
        return None

for i, addr in enumerate(remaining):
    # Skip — already done via v1 (still has data, just less strict)
    r = subprocess.run([GMGN, "portfolio", "stats", "--chain", "sol",
                        "--wallet", addr, "--period", "30d", "--raw"],
                       capture_output=True, text=True, timeout=15)
    
    if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"\nRATE LIMIT at {i+1}/{len(remaining)} - saved {len(verified)}")
        sys.exit(0)
    
    try:
        d = json.loads(r.stdout)
        last_ts = d.get("last_timestamp", 0)
        tokens_traded = d.get("pnl_stat", {}).get("token_num", 0)
        realized = float(d.get("realized_profit", 0) or 0)
        buy = d.get("buy", 0)
        sell = d.get("sell", 0)
        
        # REAL criteria
        has_activity = last_ts > 0 and tokens_traded > 0
        has_profit = has_activity and realized > 0
        
        # On-chain check — only for wallet with apparent activity (skip the obvious fakes)
        # Actually, lets do it for all to be thorough
        on_chain_exists = rpc_check(addr)
        
        is_real = has_activity and on_chain_exists is True
        
        verified[addr] = {
            "last_timestamp": last_ts,
            "tokens_traded_30d": tokens_traded,
            "realized_profit_30d": realized,
            "buy_30d": buy,
            "sell_30d": sell,
            "on_chain_exists": on_chain_exists,
            "is_verified": is_real,
            "has_profit": has_profit and is_real,
        }
    except Exception:
        continue
    
    if (i + 1) % 25 == 0:
        real = sum(1 for v in verified.values() if v["is_verified"])
        profit = sum(1 for v in verified.values() if v.get("has_profit"))
        nonexist = sum(1 for v in verified.values() if v.get("on_chain_exists") is False)
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"[{i+1}/{len(remaining)}] {real} real, {profit} profitable, {nonexist} on-chain phantom (total: {len(verified)})", flush=True)
    
    time.sleep(1.0)  # balance speed + safety

VERIF_OUT.write_text(json.dumps(verified))
real = sum(1 for v in verified.values() if v["is_verified"])
profit = sum(1 for v in verified.values() if v.get("has_profit"))
nonexist = sum(1 for v in verified.values() if v.get("on_chain_exists") is False)
print(f"\nDONE: {len(verified)}/{len(sorted_wallets)} checked")
print(f"  Real (active + on-chain): {real}")
print(f"  Profitable: {profit}")
print(f"  Phantom (no on-chain account): {nonexist}")
