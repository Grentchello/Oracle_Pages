#!/usr/bin/env python3
"""
Build smart money wallet LIST from GMGN trenches endpoint.

v2: Pulls from all 3 categories (completed, near_completion, new_creation)
    with quality filters, finds true winners across multiple tokens.
"""
import subprocess
import json
import time
from pathlib import Path

GMGN_CLI = "/opt/data/home/.npm-global/bin/gmgn-cli"
CHAIN = "sol"
OUTPUT = Path("/opt/data/hermes_work/bot/copy_trading/wallets_smart_money.json")


def _run(args, timeout=30, retries=3):
    """Run gmgn-cli with retries on rate limit."""
    for attempt in range(retries):
        r = subprocess.run([GMGN_CLI] + args + ["--raw"],
                          capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except Exception:
                pass
        if "RATE_LIMIT" in r.stdout or "429" in r.stdout:
            print(f"   [RATE LIMITED] waiting 60s...")
            time.sleep(60)
        else:
            print(f"   [ERR] {r.stderr[:200] or r.stdout[:200]}")
            return None
    return None


def get_quality_tokens(category: str, limit: int = 80):
    """Get quality tokens from a category — only tokens that RAN WELL."""
    print(f"[*] Fetching '{category}' with quality filters...")
    data = _run(["market", "trenches", "--chain", CHAIN,
                 "--type", category,
                 "--filter-preset", "smart-money",
                 "--sort-by", "smart_degen_count",
                 "--min-volume-24h", "10000",
                 "--min-net-buy-24h", "5000",
                 "--min-swaps-24h", "1000",
                 "--min-visiting-count", "3",
                 "--limit", str(limit)])
    if not data:
        return []
    return data.get(category, [])


def get_token_traders(addr, limit=50):
    """Get all traders of a token."""
    # No sleep - we add delay at higher level
    return _run(["token", "traders", "--chain", CHAIN, "--address", addr,
                 "--limit", str(limit)], timeout=60)


def main():
    # Step 1: Use cached tokens or fetch fresh
    cache = Path("/opt/data/hermes_work/bot/copy_trading/cache/tokens_100.json")
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 3600:
        cached = json.load(open(cache))
        if len(cached) >= 50:
            print(f"[*] Using cached tokens ({len(cached)} tokens from {time.strftime('%H:%M:%S', time.localtime(cache.stat().st_mtime))})")
            # Restore full token data (fetched has minimal fields)
            tokens = [{"address": t["address"], "symbol": t.get("symbol", "?"), "smart_degen_count": t.get("smart_degen_count", 0)} for t in cached]
        else:
            tokens = None
    else:
        tokens = None

    if not tokens:
        # Fresh fetch
        all_tokens = []
        for cat in ["completed", "near_completion", "new_creation"]:
            tokens = get_quality_tokens(cat, limit=80)
            all_tokens.extend(tokens)
            print(f"   {cat}: got {len(tokens)} tokens")

        seen = set()
        tokens = []
        for t in all_tokens:
            a = t.get("address")
            if a and a not in seen:
                seen.add(a)
                tokens.append(t)
        print(f"\n[*] Total unique tokens: {len(tokens)}")

        tokens.sort(key=lambda t: t.get("smart_degen_count", 0), reverse=True)
        tokens = tokens[:100]

    # Step 2: For each token, get top traders with positive PnL
    wallet_trades = {}
    cache_path = Path("/opt/data/hermes_work/bot/copy_trading/cache/wallets_in_progress.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        try:
            wallet_trades = json.load(open(cache_path))
            print(f"   [RESUME] loaded {len(wallet_trades)} wallets from cache")
        except Exception:
            pass

    for i, t in enumerate(tokens):
        addr = t.get("address")
        sym = t.get("symbol", "?")
        sd = t.get("smart_degen_count", 0)
        mc = t.get("market_cap", 0)
        print(f"[{i+1}/{len(tokens)}] {sym:10s} (smart_d={sd}, mc=${mc:,.0f}) ", end="", flush=True)

        traders = get_token_traders(addr, limit=80)
        if not traders:
            print("[FAIL]")
            time.sleep(2.0)
            continue

        winners_added = 0
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
            winners_added += 1

        print(f"({winners_added} winners)")

        # Save progress every 5 tokens
        if (i + 1) % 5 == 0:
            save_results(wallet_trades, tokens[:i+1], in_progress=True)
            print(f"   [saved {len(wallet_trades)} wallets so far]")

        # Rate limit protection
        time.sleep(2.0)

    # Final save — PRE-VERIFICATION REMINDER
    # Wallets where GMGN portfolio stats shows 0 trades are SUSPICIOUS
    # (exist in "traders" endpoint but have no real trades)
    # Verify top wallets with: gmgn-cli portfolio stats --chain sol --wallet <addr>

    # Final save
    save_results(wallet_trades, tokens, in_progress=False)

    # Top 10 wallets to verify
    ranked = []
    for w, trades in wallet_trades.items():
        ranked.append({
            "wallet": w,
            "total_pnl_sol": sum(t["pnl_sol"] for t in trades),
            "tokens_traded": len(set(t["token_address"] for t in trades)),
            "tokens_unique": len(set(t["token"] for t in trades)),
            "trades": trades,
        })
    ranked.sort(key=lambda x: x["total_pnl_sol"], reverse=True)

    print("\n⚠️  VERIFY top 20 wallets (portfolio stats check):")
    for w in ranked[:20]:
        print(f"   gmgn-cli portfolio stats --chain sol --wallet {w['wallet']} --period 30d --raw")
    print()
    print("If any shows last_timestamp=0 or buy=0, that wallet is fabricated.")


def save_results(wallet_trades, tokens, in_progress=False):
    ranked = []
    for w, trades in wallet_trades.items():
        ranked.append({
            "wallet": w,
            "total_pnl_sol": sum(t["pnl_sol"] for t in trades),
            "tokens_traded": len(set(t["token_address"] for t in trades)),
            "tokens_unique": len(set(t["token"] for t in trades)),
            "trades": trades,
        })
    ranked.sort(key=lambda x: x["total_pnl_sol"], reverse=True)

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chain": CHAIN,
        "in_progress": in_progress,
        "tokens_analyzed": len(tokens),
        "tokens_unique_by_address": len(set(t.get("address") for t in tokens)),
        "wallets_found": len(ranked),
        "wallets_with_2plus_tokens": sum(1 for w in ranked if w["tokens_traded"] >= 2),
        "wallets_with_3plus_tokens": sum(1 for w in ranked if w["tokens_traded"] >= 3),
        "top_wallets": ranked[:100],
    }
    OUTPUT.write_text(json.dumps(output, indent=2))

    if in_progress:
        print(f"   [progress saved: {len(ranked)} wallets, {output['wallets_with_2plus_tokens']} won 2+ times]")
    else:
        print(f"\n[*] FINAL: Saved {len(ranked)} wallets to {OUTPUT}")
        print(f"[*] Wallets winning on 2+ tokens: {output['wallets_with_2plus_tokens']}")
        print(f"[*] Wallets winning on 3+ tokens: {output['wallets_with_3plus_tokens']}")
        print("\nTop 30 by total PnL:")
        for w in ranked[:30]:
            tcount = w["tokens_traded"]
            syms = ", ".join(set(t["token"] for t in w["trades"][:4]))
            print(f"  {w['wallet'][:12]}... total={w['total_pnl_sol']:.0f} SOL  ({tcount} tokens)  {syms}")


if __name__ == "__main__":
    main()
