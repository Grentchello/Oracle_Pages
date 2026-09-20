#!/usr/bin/env python3
"""
Build smart money wallet LIST from GMGN trenches endpoint.
Strategy:
  1. Get completed tokens (smart-money preset)
  2. For top tokens by smart_degen_count, fetch top traders
  3. Aggregate wallet addresses that appear across multiple tokens
  4. Save unique wallets to wallets_smart_money.json

Output: list of wallets with PnL across multiple winning tokens.
"""
import subprocess
import json
import time
from pathlib import Path

GMGN_CLI = "/opt/data/home/.npm-global/bin/gmgn-cli"
CHAIN = "sol"
OUTPUT = Path("/opt/data/hermes_work/bot/copy_trading/wallets_smart_money.json")


def _run(args, timeout=120):
    try:
        r = subprocess.run([GMGN_CLI] + args + ["--raw"], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            print(f"[ERR] {args[0]}: {r.stderr[:200]}")
            return None
        return json.loads(r.stdout)
    except Exception as e:
        print(f"[ERR] {e}")
        return None


def get_top_tokens_with_smart_money(limit=30, min_smart_degens=20):
    """Get completed pump.fun tokens with high smart_degen counts."""
    print(f"[*] Fetching top tokens with smart-money preset...")
    data = _run(["market", "trenches", "--chain", CHAIN,
                 "--type", "completed",
                 "--filter-preset", "smart-money",
                 "--limit", str(limit)])
    if not data:
        return []

    tokens = data.get("completed", [])
    # Sort by smart_degen_count
    tokens = [t for t in tokens if t.get("smart_degen_count", 0) >= min_smart_degens]
    tokens.sort(key=lambda t: t.get("smart_degen_count", 0), reverse=True)
    return tokens


def get_token_traders(token_address, limit=50):
    """Get all traders of a token with their PnL."""
    time.sleep(2.0)  # rate limit
    return _run(["token", "traders", "--chain", CHAIN, "--address", token_address,
                 "--limit", str(limit)], timeout=60)


def main():
    # Step 1: Get top tokens (these are "winning" tokens where smart money made money)
    tokens = get_top_tokens_with_smart_money(limit=30, min_smart_degens=20)
    print(f"[*] Got {len(tokens)} tokens with 20+ smart-degens")

    if not tokens:
        print("[!] No tokens found")
        return

    # Step 2: For each top token, get top traders (those with positive PnL)
    wallet_trades = {}  # wallet -> [{token, pnl, ...}]

    for i, t in enumerate(tokens[:15]):  # limit to 15 tokens to avoid rate limits
        addr = t.get("address")
        sym = t.get("symbol", "?")
        print(f"\n[{i+1}/15] {sym} ({addr[:12]}...) - {t.get('smart_degen_count')} smart-degens")

        traders = get_token_traders(addr, limit=80)
        if not traders:
            continue

        for tr in traders.get("list", []):
            w = tr.get("account_address")
            pnl = float(tr.get("realized_profit", 0) or 0)
            if not w or pnl <= 0:
                continue
            if w not in wallet_trades:
                wallet_trades[w] = []
            wallet_trades[w].append({
                "token": sym,
                "token_address": addr,
                "pnl_sol": pnl,
                "pnl_pct": float(tr.get("realized_pnl", 0) or 0),
            })

        # Save progress
        if (i + 1) % 5 == 0:
            save_results(wallet_trades)
            print(f"   [saved progress: {len(wallet_trades)} wallets so far]")

    # Step 3: Rank wallets by total PnL across multiple tokens
    ranked = []
    for w, trades in wallet_trades.items():
        total_pnl = sum(t["pnl_sol"] for t in trades)
        tokens_count = len(set(t["token_address"] for t in trades))
        ranked.append({
            "wallet": w,
            "total_pnl_sol": total_pnl,
            "tokens_traded": tokens_count,
            "trades": trades,
        })

    ranked.sort(key=lambda x: x["total_pnl_sol"], reverse=True)

    # Save
    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chain": CHAIN,
        "tokens_analyzed": len(tokens[:15]),
        "wallets_found": len(ranked),
        "wallets_with_2plus_tokens": sum(1 for w in ranked if w["tokens_traded"] >= 2),
        "top_wallets": ranked[:100],  # top 100 by total PnL
    }

    OUTPUT.write_text(json.dumps(output, indent=2))
    print(f"\n[*] Saved {len(ranked)} wallets to {OUTPUT}")
    print(f"\nTop 10 by total PnL:")
    for w in ranked[:10]:
        print(f"  {w['wallet'][:12]}... total={w['total_pnl_sol']:.0f} SOL  ({w['tokens_traded']} tokens)")


def save_results(wallet_trades):
    """Save intermediate progress."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ranked = []
    for w, trades in wallet_trades.items():
        ranked.append({
            "wallet": w,
            "total_pnl_sol": sum(t["pnl_sol"] for t in trades),
            "tokens_traded": len(set(t["token_address"] for t in trades)),
            "trades": trades,
        })
    ranked.sort(key=lambda x: x["total_pnl_sol"], reverse=True)
    OUTPUT.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chain": CHAIN,
        "in_progress": True,
        "wallets_found": len(ranked),
        "top_wallets": ranked[:50],
    }, indent=2))


if __name__ == "__main__":
    main()
