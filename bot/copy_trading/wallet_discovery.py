#!/usr/bin/env python3
"""
Copy-trading wallet discovery via GMGN API.
Strategy:
  1. Pull smart-money buy signals (signal-type=5) over recent period
  2. Extract unique wallet addresses (makers)
  3. Score each wallet on 60-day window:
     - Win rate (portfolio stats 30d + profits all)
     - Realized profit
     - Unique tokens traded
     - Hold time pattern (no instant roundtrips = bot)
  4. EXCLUDE anti-copier wash strategies:
     - wash_trader tag
     - buy-sell within 5 seconds (sandwiching copiers)
     - sells > buys ratio (dumping on copiers)
     - bundled with same-block buys (coordinated dump)
     - renamed repeatedly (avoiding blacklist)
  5. Output top 50+ sorted by 60-day score
"""
import subprocess
import json
import sys
import time
from pathlib import Path
from typing import Optional

GMGN_CLI = "/opt/data/home/.npm-global/bin/gmgn-cli"
CHAIN = "sol"

CACHE_DIR = Path("/opt/data/hermes_work/bot/copy_trading/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _run(args: list, timeout: int = 60) -> Optional[dict]:
    try:
        r = subprocess.run([GMGN_CLI] + args + ["--raw"], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            print(f"[ERR] gmgn-cli {args}: {r.stderr[:200]}", file=sys.stderr)
            return None
        return json.loads(r.stdout)
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] gmgn-cli {args}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[JSON ERR] {e}: {r.stdout[:200]}", file=sys.stderr)
        return None


def get_smart_money_trades(limit: int = 200) -> list:
    """Pull recent smart-money tagged trades."""
    data = _run(["track", "smartmoney", "--chain", CHAIN, "--limit", str(limit)], timeout=120)
    if not data:
        return []
    return data.get("list", data) if isinstance(data, dict) else data


def get_wallet_stats(wallets: list, period: str = "30d") -> dict:
    """Get trading stats — one wallet per call (GMGN CLI limitation).
    Returns dict keyed by wallet address.
    """
    out = {}
    for w in wallets:
        data = _run(["portfolio", "stats", "--chain", CHAIN, "--period", period, "--wallet", w], timeout=60)
        if data and isinstance(data, dict) and "wallet_address" in data:
            out[w] = data
        time.sleep(0.5)  # rate limit
    return out


def get_wallet_profits(wallets: list, period: str = "all") -> dict:
    """Get all-time PnL — one wallet per call (GMGN CLI limitation).
    Returns dict keyed by wallet address.
    """
    out = {}
    for w in wallets:
        data = _run(["portfolio", "profits", "--chain", CHAIN, "--period", period, "--wallet", w], timeout=60)
        if data and isinstance(data, dict) and "list" in data:
            for entry in data["list"]:
                addr = entry.get("wallet_address")
                if addr:
                    out[addr] = entry
        elif data and isinstance(data, dict) and "wallet_address" in data:
            out[w] = data
        time.sleep(0.5)
    return out


# Anti-copier wash strategy tags (GMGN labels these explicitly)
ANTI_COPIER_TAGS = {
    "wash_trader",          # Explicitly flagged
    "bundler",              # Buys multiple in same tx
    "snipe_bot",            # MEV / first block
    "bot",                  # General bot
}


def detect_wash_pattern(wallet: str, recent_trades: list) -> dict:
    """Detect anti-copier strategies from a wallet's trade history."""
    wallet_trades = [t for t in recent_trades if t.get("maker") == wallet]
    if len(wallet_trades) < 5:
        return {"wash_score": 0, "flags": ["insufficient_data"], "trades": len(wallet_trades)}

    flags = []
    wash_score = 0

    # 1. Buy-sell within 5s (sandwiching copiers)
    # Sort by timestamp
    sorted_t = sorted(wallet_trades, key=lambda x: x.get("timestamp", 0))
    instant_roundtrips = 0
    buys = [t for t in sorted_t if t.get("side") == "buy"]
    sells = [t for t in sorted_t if t.get("side") == "sell"]
    for b in buys:
        for s in sells:
            if abs(b.get("timestamp", 0) - s.get("timestamp", 0)) < 5 and b.get("base_address") == s.get("base_address"):
                instant_roundtrips += 1
    if instant_roundtrips > 2:
        wash_score += instant_roundtrips
        flags.append(f"instant_roundtrip_{instant_roundtrips}")

    # 2. Sells > buys (dumping on copiers)
    total_buy_usd = sum(float(t.get("amount_usd", 0) or 0) for t in buys)
    total_sell_usd = sum(float(t.get("amount_usd", 0) or 0) for t in sells)
    if total_sell_usd > 0 and total_buy_usd > 0:
        sell_buy_ratio = total_sell_usd / total_buy_usd
        if sell_buy_ratio > 0.85:  # Sells > 85% of buys = dumping
            wash_score += 3
            flags.append(f"high_sell_ratio_{sell_buy_ratio:.2f}")

    # 3. Renamed wallets (avoiding blacklist) — check maker_info
    # We can see this in their token entries
    # Skip for now (not in trade data)

    # 4. Bundled buys (same-block buys)
    # Group by timestamp (same block)
    from collections import Counter
    ts_counter = Counter(t.get("timestamp") for t in buys)
    bundled = sum(1 for c in ts_counter.values() if c > 2)
    if bundled > 0:
        wash_score += bundled * 2
        flags.append(f"bundled_buys_{bundled}")

    # 5. Repeated small buys + larger sells (copy-trap)
    # If avg buy is < $20 and any sell > $500 — possible trap
    if buys and sells:
        avg_buy = total_buy_usd / len(buys)
        max_sell = max((float(s.get("amount_usd", 0) or 0) for s in sells), default=0)
        if avg_buy < 20 and max_sell > 500:
            wash_score += 2
            flags.append("small_buy_large_sell_pattern")

    # 6. HIGH FREQUENCY TRADER: trades every ~2 min on average
    # Real strategy has think time. Bots/snipers fire constantly.
    if len(wallet_trades) >= 10:
        sorted_t = sorted(wallet_trades, key=lambda x: x.get("timestamp", 0))
        ts_deltas = []
        for i in range(1, len(sorted_t)):
            d = sorted_t[i].get("timestamp", 0) - sorted_t[i-1].get("timestamp", 0)
            if d > 0:
                ts_deltas.append(d)
        if ts_deltas:
            avg_interval_sec = sum(ts_deltas) / len(ts_deltas)
            if avg_interval_sec < 120:  # avg less than 2 min between trades = bot
                wash_score += 4
                flags.append(f"high_freq_{int(avg_interval_sec)}s_avg")

    # 7. SAME-TOKEN REPEAT FLIPPER: buys/sells same token multiple times rapidly
    # Example: buy DOGE, sell DOGE, buy DOGE, sell DOGE every 15s for 2 min
    # Pattern: count consecutive opposite-side trades on same token within 5 min windows
    same_token_flips = 0
    if len(wallet_trades) >= 4:
        sorted_t = sorted(wallet_trades, key=lambda x: x.get("timestamp", 0))
        # Group by base_address + look for rapid side flips
        from collections import defaultdict
        by_token = defaultdict(list)
        for t in sorted_t:
            by_token[t.get("base_address")].append(t)
        for token_addr, token_trades in by_token.items():
            if len(token_trades) < 4:
                continue
            # Sliding window: count side flips in 5-min windows
            for i in range(len(token_trades)):
                window = []
                for j in range(i, len(token_trades)):
                    if token_trades[j].get("timestamp", 0) - token_trades[i].get("timestamp", 0) <= 300:
                        window.append(token_trades[j])
                    else:
                        break
                if len(window) >= 4:
                    sides = [w.get("side") for w in window]
                    flips = sum(1 for k in range(1, len(sides)) if sides[k] != sides[k-1])
                    if flips >= 3:  # 3+ side flips in 5 min on same token = flippping
                        same_token_flips += 1
                        break  # count this token once
    if same_token_flips > 0:
        wash_score += 3 * same_token_flips
        flags.append(f"token_flipper_{same_token_flips}_tokens")

    # 8. MULTI-TOKEN PER TX: trades where 1 tx contains 3+ different tokens
    # Real traders buy/sell ONE token at a time. Wealth transfers / bridges move many at once.
    multi_token_txs = 0
    from collections import defaultdict
    tx_tokens = defaultdict(set)
    for t in wallet_trades:
        tx = t.get("tx_hash") or t.get("transaction_hash")
        token = t.get("base_address")
        if tx and token:
            tx_tokens[tx].add(token)
    for tx, tokens in tx_tokens.items():
        if len(tokens) >= 3:
            multi_token_txs += 1
    if multi_token_txs >= 5:
        wash_score += 5
        flags.append(f"multi_token_txs_{multi_token_txs}_txs")
    elif multi_token_txs >= 2:
        wash_score += 2
        flags.append(f"multi_token_txs_{multi_token_txs}_txs")

    # 9. ATOMIC PAIR TRADES: tx with buy + sell of different tokens in same tx
    # Real strategy: buy token, hold, sell later. Bridge: swap A→B atomically.
    atomic_pair_txs = 0
    tx_sides = defaultdict(lambda: {"buy": set(), "sell": set()})
    for t in wallet_trades:
        tx = t.get("tx_hash") or t.get("transaction_hash")
        side = t.get("side") or t.get("event_type")
        token = t.get("base_address")
        if tx and side and token:
            tx_sides[tx][side].add(token)
    for tx, sides in tx_sides.items():
        if sides.get("buy") and sides.get("sell"):
            # Tokens being bought != tokens being sold in same tx = atomic swap
            atomic_pair_txs += 1
    if atomic_pair_txs >= 10:
        wash_score += 4
        flags.append(f"atomic_swaps_{atomic_pair_txs}_txs")
    elif atomic_pair_txs >= 3:
        wash_score += 2
        flags.append(f"atomic_swaps_{atomic_pair_txs}_txs")

    return {"wash_score": wash_score, "flags": flags, "trades": len(wallet_trades)}


def main():
    print("[*] Pulling recent smart-money trades...")
    trades = get_smart_money_trades(limit=200)  # GMGN max is 200 per call
    print(f"[*] Got {len(trades)} recent trades")

    if not trades:
        print("[!] No trades — exiting")
        return

    # Extract unique wallets (makers) and their tags
    wallet_tags = {}  # addr -> tags
    for t in trades:
        m = t.get("maker")
        if not m:
            continue
        if m not in wallet_tags:
            wallet_tags[m] = []
        mi = t.get("maker_info", {})
        for tag in mi.get("tags", []):
            if tag not in wallet_tags[m]:
                wallet_tags[m].append(tag)

    print(f"[*] {len(wallet_tags)} unique wallets in recent trades")

    # Initial filter: exclude anti-copier tags
    candidates = []
    excluded = []
    for w, tags in wallet_tags.items():
        bad = any(t in ANTI_COPIER_TAGS for t in tags)
        if bad:
            excluded.append((w, tags))
        else:
            candidates.append(w)
    print(f"[*] After anti-copier tag filter: {len(candidates)} candidates, {len(excluded)} excluded")

    if not candidates:
        print("[!] No candidates left after tag filter — try larger trade set")
        return

    # Get 30d stats (GMGN doesn't support 60d — approximate with 30d)
    print(f"[*] Fetching 30d stats for {len(candidates)} wallets...")
    stats_30d = get_wallet_stats(candidates, period="30d")
    time.sleep(2)

    # Get all-time profits
    print(f"[*] Fetching all-time profits for {len(candidates)} wallets...")
    profits_all = get_wallet_profits(candidates, period="all")
    time.sleep(2)

    # Score and filter
    scored = []
    debug = []
    for w in candidates:
        s30 = stats_30d.get(w, {})
        pa = profits_all.get(w, {})

        if not s30 and not pa:
            debug.append((w, "no_stats_no_profits"))
            continue

        # 30d win rate (GMGN uses nested pnl_stat)
        pnl_stat = s30.get("pnl_stat", {}) or {}
        win_rate = float(pnl_stat.get("winrate", 0) or 0) * 100
        realized_30d = float(s30.get("realized_profit", 0) or 0)
        unique_tokens = int(pnl_stat.get("token_num", 0) or 0)
        total_trades_30d = int(s30.get("buy", 0) or 0) + int(s30.get("sell", 0) or 0)

        # All-time PnL (profits API uses flat fields)
        pa_list = pa if isinstance(pa, list) else [pa] if pa else []
        pa_first = pa_list[0] if pa_list else {}
        realized_all = float(pa_first.get("total_realized_profit", pa_first.get("realized_profit", 0)) or 0)
        win_rate_all = 0  # not in profits API
        pa = pa_first  # simplify downstream usage

        # Wash pattern detection
        wash = detect_wash_pattern(w, trades)

        # Skip if insufficient data
        if total_trades_30d < 5:
            continue

        # Skip low win rate (30% is OK for memecoin volatility)
        if win_rate < 30:
            continue

        # Skip if anti-copier wash detected
        if wash["wash_score"] >= 5:
            print(f"[WASH] {w[:10]}... score={wash['wash_score']} flags={wash['flags']}")
            continue

        # Composite score (60-day proxy: weight 30d + all-time)
        # Score = realized_profit * (win_rate/100) * log(unique_tokens + 1)
        import math
        score = realized_30d * (win_rate / 100) * math.log(unique_tokens + 1) - wash["wash_score"] * 10

        scored.append({
            "wallet": w,
            "score": score,
            "win_rate_30d": win_rate,
            "realized_profit_30d_sol": realized_30d,
            "unique_tokens_30d": unique_tokens,
            "total_trades_30d": total_trades_30d,
            "win_rate_all": win_rate_all,
            "realized_profit_all_sol": realized_all,
            "tags": wallet_tags[w],
            "wash_score": wash["wash_score"],
            "wash_flags": wash["flags"],
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Debug output
    print(f"\n[*] DEBUG: {len(debug)} wallets dropped, sample:")
    for w, reason in debug[:5]:
        print(f"    {w[:12]}... reason={reason}")
    print(f"[*] DEBUG: stats_30d keys: {len(stats_30d)}, profits_all keys: {len(profits_all)}")
    if stats_30d:
        sample_addr = list(stats_30d.keys())[0]
        print(f"[*] DEBUG: sample stats[0] = {json.dumps(stats_30d[sample_addr], indent=2)[:500]}")

    # Output
    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chain": CHAIN,
        "window": "30d primary, all-time secondary (60d proxy)",
        "total_candidates_after_tag_filter": len(candidates),
        "total_wallets_scored": len(scored),
        "anti_copier_filter": list(ANTI_COPIER_TAGS),
        "top_traders": scored[:60],
    }

    out_file = Path("/opt/data/hermes_work/bot/copy_trading/top_traders_60d.json")
    out_file.write_text(json.dumps(output, indent=2))
    print(f"[*] Saved top {len(scored[:60])} traders to {out_file}")

    # Print top 10
    print("\n=== TOP 10 (60-day proxy score) ===")
    for i, t in enumerate(scored[:10], 1):
        wr = t['win_rate_30d']
        pnl = t['realized_profit_30d_sol']
        tokens = t['unique_tokens_30d']
        sc = t['score']
        wsh = t['wash_score']
        wallet_short = t['wallet'][:8]
        print(f"{i:2}. {wallet_short}... WR30d={wr:.1f}% PnL30d={pnl:.2f} SOL tokens={tokens} score={sc:.1f} wash={wsh}")


if __name__ == "__main__":
    main()
