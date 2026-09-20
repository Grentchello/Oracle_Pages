#!/usr/bin/env python3
"""Get token holdings for each wallet + USD value via DexScreener."""
import json, time, urllib.request, sys
from pathlib import Path

BALANCES = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_balance.json"))
TX_COUNT = json.load(open("/opt/data/hermes_work/bot/copy_trading/cache/wallets_tx_count.json"))

# Wallets with >0 SOL or that have transactions
wallets = list(BALANCES.keys())
print(f"Wallets to check: {len(wallets)}")

OUT = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_holdings.json")
if OUT.exists():
    holdings = json.load(open(OUT))
else:
    holdings = {}

RPC = "https://api.mainnet-beta.solana.com"
SOL_PRICE = 222  # current SOL price USD (approx Sep 2026)

import urllib.request

def get_token_accounts(addr):
    """Get all SPL token balances for a wallet."""
    try:
        req = urllib.request.Request(RPC, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner",
            "params": [addr, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            accounts = d.get("result", {}).get("value", [])
            tokens = []
            for a in accounts:
                try:
                    info = a["account"]["data"]["parsed"]["info"]
                    mint = info["mint"]
                    amount = float(info["tokenAmount"]["uiAmount"] or 0)
                    if amount > 0:
                        tokens.append({"mint": mint, "amount": amount})
                except Exception:
                    continue
            return tokens
    except Exception:
        return None

remaining = [a for a in wallets if a not in holdings]
print(f"Remaining: {len(remaining)}")

for i, addr in enumerate(remaining):
    tokens = get_token_accounts(addr)
    if tokens is None:
        holdings[addr] = {"error": "rpc fail"}
        continue
    
    holdings[addr] = {
        "sol_balance": BALANCES.get(addr, {}).get("sol", 0),
        "token_count": len(tokens),
        "tokens": tokens[:50],  # cap
        "tx_30d": TX_COUNT.get(addr, {}).get("recent_txs_30d", 0),
    }
    
    if (i + 1) % 50 == 0:
        OUT.write_text(json.dumps(holdings))
        real = sum(1 for v in holdings.values() if v.get("token_count", 0) > 0)
        print(f"  [{i+1}/{len(remaining)}] {real} hold tokens", flush=True)
    
    time.sleep(0.05)

OUT.write_text(json.dumps(holdings))
real = sum(1 for v in holdings.values() if v.get("token_count", 0) > 0)
print(f"\nDone: {len(holdings)} wallets")
print(f"  With token holdings: {real}")
