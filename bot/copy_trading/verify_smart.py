#!/usr/bin/env python3
"""Smart verification: batch RPC first, then GMGN only for real wallets."""
import json, time, sys, urllib.request
from pathlib import Path

TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
VERIF_OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_verified_v3.json")

# Load v2 results as baseline
v2_path = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_verified_all_v2.json")
v2 = {}
if v2_path.exists():
    v2 = json.load(open(v2_path))

# Use v2 results as starting point
verified = dict(v2)

# Find remaining wallets
wallet_pnl = {w: sum(t["pnl_sol"] for t in ts) for w, ts in TRADES.items()}
sorted_wallets = sorted(wallet_pnl.keys(), key=lambda w: wallet_pnl[w], reverse=True)
remaining = [a for a in sorted_wallets if a not in verified]

print(f"Total: {len(sorted_wallets)}")
print(f"Already verified (from v2): {len(verified)}")
print(f"Remaining: {len(remaining)}")
print()
print("Step 1: batch RPC check on remaining wallets...")
sys.stdout.flush()

RPC = "https://api.mainnet-beta.solana.com"

def rpc_batch_check(addrs, batch_size=100):
    """Batch call getMultipleAccountsInfo."""
    results = {}
    for i in range(0, len(addrs), batch_size):
        batch = addrs[i:i+batch_size]
        try:
            req = urllib.request.Request(RPC, data=json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "getMultipleAccountsInfo",
                "params": [batch, {"encoding": "base64"}]
            }).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                d = json.loads(resp.read())
                values = d.get("result", {}).get("value", [])
                for addr, val in zip(batch, values):
                    results[addr] = val is not None
        except Exception as e:
            print(f"  Batch error at {i}: {e}")
            # Mark all as None
            for addr in batch:
                results[addr] = None
        time.sleep(0.2)
    return results

rpc_results = rpc_batch_check(remaining)
print(f"RPC: {sum(1 for v in rpc_results.values() if v is True)} exist, "
      f"{sum(1 for v in rpc_results.values() if v is False)} phantom, "
      f"{sum(1 for v in rpc_results.values() if v is None)} unknown")

# Update verif: mark phantoms first
phantom_count = 0
real_count = 0
for addr in remaining:
    if addr not in verified:
        verified[addr] = {
            "last_timestamp": 0,
            "tokens_traded_30d": 0,
            "realized_profit_30d": 0,
            "buy_30d": 0,
            "sell_30d": 0,
            "is_verified": False,
            "has_profit": False,
            "on_chain_exists": rpc_results.get(addr),
            "_pending_gmgn": rpc_results.get(addr) is True,
        }
        if rpc_results.get(addr) is False:
            phantom_count += 1
        elif rpc_results.get(addr) is True:
            real_count += 1

VERIF_OUT.write_text(json.dumps(verified))
print(f"Marked {phantom_count} as PHANTOM (no on-chain account)")
print(f"Need GMGN check on {real_count} wallets that DO exist on-chain")
print()

# Now do GMGN check on the ones that exist (smaller batch)
gmgn_targets = [a for a in remaining if rpc_results.get(a) is True]
print(f"Step 2: GMGN portfolio stats on {len(gmgn_targets)} real on-chain wallets...")

GMGN = "/opt/data/home/.npm-global/bin/gmgn-cli"

for i, addr in enumerate(gmgn_targets):
    r = subprocess.run([GMGN, "portfolio", "stats", "--chain", "sol",
                        "--wallet", addr, "--period", "30d", "--raw"],
                       capture_output=True, text=True, timeout=15)
    
    if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"\nRATE LIMIT at {i+1}/{len(gmgn_targets)}")
        sys.exit(0)
    
    try:
        d = json.loads(r.stdout)
        last_ts = d.get("last_timestamp", 0)
        tokens_traded = d.get("pnl_stat", {}).get("token_num", 0)
        realized = float(d.get("realized_profit", 0) or 0)
        buy = d.get("buy", 0)
        sell = d.get("sell", 0)
        
        has_activity = last_ts > 0 and tokens_traded > 0
        is_real = has_activity and realized > 0
        
        verified[addr] = {
            "last_timestamp": last_ts,
            "tokens_traded_30d": tokens_traded,
            "realized_profit_30d": realized,
            "buy_30d": buy,
            "sell_30d": sell,
            "on_chain_exists": True,
            "is_verified": is_real,
            "has_profit": is_real,
        }
    except Exception:
        continue
    
    if (i + 1) % 10 == 0:
        real_traders = sum(1 for v in verified.values() if v["is_verified"])
        VERIF_OUT.write_text(json.dumps(verified))
        print(f"  [{i+1}/{len(gmgn_targets)}] {real_traders} verified real", flush=True)
    
    time.sleep(3.0)

VERIF_OUT.write_text(json.dumps(verified))
print()
real_traders = sum(1 for v in verified.values() if v["is_verified"])
profitable = sum(1 for v in verified.values() if v.get("has_profit"))
phantoms = sum(1 for v in verified.values() if v.get("on_chain_exists") is False)
print(f"FINAL: {len(verified)}/{len(sorted_wallets)} wallets")
print(f"  Real (trades + on-chain): {real_traders}")
print(f"  Profitable: {profitable}")
print(f"  Phantom (no on-chain account): {phantoms}")
