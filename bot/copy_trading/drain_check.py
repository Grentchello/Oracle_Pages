#!/usr/bin/env python3
"""Detect 'wealth transfer' / drain pattern for the 55 organic small-PnL traders."""
import json, time, urllib.request
from pathlib import Path

# Load the 55 organic small-PnL traders
TRADES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/all_wallet_trades.json"))
TX_COUNT_V2 = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count_v2.json"))

target = []
for w, ts in TRADES.items():
    total_pnl = sum(t["pnl_sol"] for t in ts)
    if 5 <= total_pnl <= 20:
        tx = TX_COUNT_V2.get(w, {}).get("recent_txs_30d", 0)
        if 5 <= tx <= 49:
            target.append((w, total_pnl, tx))

print(f"Target wallets to check drain: {len(target)}")

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_drain.json")
if OUT.exists():
    drain = json.load(open(OUT))
else:
    drain = {}

RPC = "https://api.mainnet-beta.solana.com"

for i, (addr, pnl, tx) in enumerate(target):
    if addr in drain and 'tx_analyzed' in drain[addr]:
        continue
    
    try:
        # Get most recent signatures (10)
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
            "params": [addr, {"limit": 10}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            sigs = d.get("result", [])
        
        if not sigs:
            drain[addr] = {"tx_analyzed": 0, "note": "no txs"}
            continue
        
        # For each, fetch full transaction and check SOL balance changes
        sol_in = 0
        sol_out = 0
        unique_destinations = set()
        big_transfers = []  # transfers > 0.5 SOL
        
        for sig_info in sigs[:8]:
            sig = sig_info["signature"]
            try:
                req = urllib.request.Request(RPC, data=json.dumps({
                    "jsonrpc": "2.0", "id": 1, "method": "getTransaction",
                    "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
                }).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    tx = json.loads(resp.read())
                    result = tx.get("result", {})
                    if not result:
                        continue
                    msg = result.get("transaction", {}).get("message", {})
                    keys = msg.get("accountKeys", [])
                    if addr not in keys:
                        continue
                    idx = keys.index(addr)
                    pre = result.get("meta", {}).get("preBalances", [0] * len(keys))
                    post = result.get("meta", {}).get("postBalances", [0] * len(keys))
                    pre_sol = pre[idx] / 1e9 if idx < len(pre) else 0
                    post_sol = post[idx] / 1e9 if idx < len(post) else 0
                    change = post_sol - pre_sol
                    
                    if change > 0.5:
                        sol_in += change
                    elif change < -0.5:
                        sol_out += abs(change)
                        big_transfers.append(abs(change))
                        # Find where SOL went
                        for j in range(len(keys)):
                            if j != idx and j < len(pre) and j < len(post):
                                if post[j] - pre[j] > 0.5:
                                    unique_destinations.add(keys[j])
                                    break
            except Exception:
                continue
        
        net = sol_in - sol_out
        drain_score = sol_out / (sol_in + sol_out + 0.001)  # 0-1 ratio of outflow
        
        drain[addr] = {
            "tx_analyzed": len(sigs[:8]),
            "sol_in_8tx": sol_in,
            "sol_out_8tx": sol_out,
            "net_flow": net,
            "destinations_count": len(unique_destinations),
            "big_transfers": big_transfers,
            "drain_ratio": drain_score,
        }
    except Exception as e:
        drain[addr] = {"error": str(e)[:100]}
    
    if (i + 1) % 5 == 0:
        OUT.write_text(json.dumps(drain))
        high_drain = sum(1 for v in drain.values() if v.get("drain_ratio", 0) > 0.7)
        print(f"[{i+1}/{len(target)}] {high_drain} high-drain, processed {len(drain)}")
    
    time.sleep(2.0)

OUT.write_text(json.dumps(drain))
high_drain = sum(1 for v in drain.values() if v.get("drain_ratio", 0) > 0.7)
balanced = sum(1 for v in drain.values() if 0.3 <= v.get("drain_ratio", 0) <= 0.7)
saver = sum(1 for v in drain.values() if v.get("drain_ratio", 0) < 0.3)
print(f"\nDONE: {len(drain)} wallets")
print(f"  Saver (<30% drain): {saver}")
print(f"  Balanced (30-70% drain): {balanced}")
print(f"  High drain (>70% drain): {high_drain}")
