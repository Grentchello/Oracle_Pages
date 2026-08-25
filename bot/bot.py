#!/usr/bin/env python3
"""
Memecoin Trading Bot — Foundation Phase

Fetches real prices from DexScreener + pump.fun, updates paper portfolio state,
records decisions. No real trading — all virtual.

Run from this script's directory:
    python3 bot.py
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
WORK_DIR = SCRIPT_DIR.parent
WIKI_DIR = WORK_DIR / "wiki"
STATE_PATH = WIKI_DIR / "trading" / "state.json"
DECISIONS_PATH = WIKI_DIR / "trading" / "decisions.md"
WATCHLIST_PATH = WIKI_DIR / "trading" / "watchlist.json"

# API endpoints
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
PUMPFUN_TOP_RUNNERS = "https://frontend-api-v3.pump.fun/coins/top-runners"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Network config
TIMEOUT = 15
USER_AGENT = "oracle-vault-memecoin-bot/0.1"


def _to_float(v, default=0.0):
    """Safely convert a value to float; returns default on None/string-conversion failure."""
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_sol_price_usd():
    """Get SOL price in USD via DexScreener SOL/USDC pair on Raydium."""
    # Querying by SOL mint returns all pairs; we want the highest-liquidity one
    url = f"{DEXSCREENER_BASE}/tokens/{SOL_MINT}"
    data = http_get_json(url)
    pairs = data.get("pairs") or []
    sol_pairs = [
        p for p in pairs
        if p.get("chainId") == "solana"
        and _to_float(p.get("priceUsd")) > 0
    ]
    if not sol_pairs:
        return None
    # Pick highest-liquidity pool for the most reliable price
    sol_pairs.sort(key=lambda p: _to_float((p.get("liquidity") or {}).get("usd")), reverse=True)
    return _to_float(sol_pairs[0]["priceUsd"])


def fetch_pumpfun_top_runners(limit=20):
    """Get top trending tokens from pump.fun."""
    try:
        data = http_get_json(PUMPFUN_TOP_RUNNERS)
        # Response shape: list of {coin: {...}}
        items = data if isinstance(data, list) else data.get("coins", [])
        out = []
        for entry in items[:limit]:
            coin = entry.get("coin", entry)
            mint = coin.get("mint")
            if not mint:
                continue
            out.append({
                "mint": mint,
                "symbol": coin.get("symbol", "?"),
                "name": coin.get("name", "?"),
                "market_cap_usd": coin.get("usd_market_cap") or coin.get("market_cap_usd"),
                "last_trade_ts": coin.get("last_trade_timestamp"),
                "complete": coin.get("complete", False),
                "source": "pump.fun top-runners",
            })
        return out
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log(f"WARN: pump.fun fetch failed: {e}")
        return []


def fetch_dexscreener_for_mints(mints):
    """Fetch DexScreener pair data for a list of mints. Returns dict mint -> pair data."""
    out = {}
    if not mints:
        return out
    # DexScreener accepts up to ~30 mints per request
    try:
        url = f"{DEXSCREENER_BASE}/tokens/{','.join(mints[:30])}"
        data = http_get_json(url)
        for pair in data.get("pairs") or []:
            mint = pair.get("baseToken", {}).get("address")
            if not mint:
                continue
            # Keep the highest-liquidity pair per mint
            existing = out.get(mint)
            new_liq = _to_float((pair.get("liquidity") or {}).get("usd"))
            existing_liq = _to_float((existing.get("liquidity") or {}).get("usd")) if existing else 0
            if existing is None or new_liq > existing_liq:
                out[mint] = pair
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log(f"WARN: DexScreener fetch failed: {e}")
    return out


def load_state():
    if not STATE_PATH.exists():
        return {
            "balance_sol": 2.0,
            "positions": {},
            "trades": [],
        }
    return json.loads(STATE_PATH.read_text())


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def load_watchlist():
    if WATCHLIST_PATH.exists():
        return json.loads(WATCHLIST_PATH.read_text())
    return None


def append_decision(decision):
    """Append a single decision line to decisions.md."""
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DECISIONS_PATH.exists():
        DECISIONS_PATH.write_text(
            "# Bot Decisions Log\n\n"
            "> Append-only log of every bot decision. Each line is one observation/thought/action.\n"
            "> Format: `## [YYYY-MM-DD HH:MM UTC] <action> | <details>`\n\n"
        )
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = f"## [{ts}] {decision['action']} | {decision['details']}\n"
    if decision.get("reason"):
        line += f"- Reasoning: {decision['reason']}\n"
    if decision.get("data"):
        line += f"- Data: `{json.dumps(decision['data'])}`\n"
    line += "\n"
    with open(DECISIONS_PATH, "a") as f:
        f.write(line)


def build_watchlist_state(sol_price, top_runners, dex_data):
    """Build a watchlist snapshot to publish to the dashboard."""
    enriched = []
    for entry in top_runners:
        mint = entry["mint"]
        pair = dex_data.get(mint)
        if pair:
            entry["price_usd"] = pair.get("priceUsd")
            entry["price_sol"] = pair.get("priceNative")
            entry["liquidity_usd"] = (pair.get("liquidity") or {}).get("usd")
            entry["volume_h24"] = (pair.get("volume") or {}).get("h24")
            entry["price_change_h24"] = (pair.get("priceChange") or {}).get("h24")
            entry["pair_url"] = pair.get("url")
        enriched.append(entry)
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sol_price_usd": sol_price,
        "tokens": enriched,
    }


def compute_portfolio_value(state, sol_price, dex_data):
    """Compute current USD value of paper positions."""
    positions_value_usd = 0.0
    for mint, pos in state.get("positions", {}).items():
        if mint == "SOL":
            positions_value_usd += pos["amount"] * sol_price
            continue
        pair = dex_data.get(mint)
        if pair and pair.get("priceUsd"):
            price = float(pair["priceUsd"])
            positions_value_usd += pos["amount"] * price
    sol_value = state.get("balance_sol", 0) * sol_price
    total = sol_value + positions_value_usd
    return {
        "sol_balance_value_usd": round(sol_value, 2),
        "positions_value_usd": round(positions_value_usd, 2),
        "total_value_usd": round(total, 2),
    }


def decide(state, sol_price, watchlist_data):
    """
    Phase 1 placeholder decision: hold position, observe.
    Phase 2 will add real strategy.
    """
    return {
        "action": "observe",
        "details": f"Phase 1 foundation — bot observes only. SOL @ ${sol_price:.2f}, "
                   f"{len(watchlist_data.get('tokens', []))} tokens on watchlist",
        "reason": "No strategy implemented yet. Phase 2 will add signal detection.",
    }


def git_commit_and_push(state_path, decisions_path):
    """Commit changes and push to origin. Trigger Pages rebuild."""
    import subprocess
    cwd = WORK_DIR
    try:
        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True, capture_output=True)
        # Check if there's anything to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True
        )
        if not result.stdout.strip():
            log("No changes to commit")
            return False
        subprocess.run(
            ["git", "commit", "-m", f"Bot update: state + decisions @ {datetime.now(timezone.utc).strftime('%H:%M')} UTC"],
            cwd=cwd, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"], cwd=cwd, check=True, capture_output=True, timeout=60
        )
        log("Pushed to oracle_Vault (will trigger Pages rebuild via cron or push)")
        return True
    except subprocess.CalledProcessError as e:
        log(f"ERROR git: {e}")
        return False


def main():
    log("=== Memecoin bot tick ===")
    state = load_state()

    # 1. Fetch SOL price
    try:
        sol_price = fetch_sol_price_usd()
        if sol_price is None:
            log("ERROR: couldn't fetch SOL price")
            sys.exit(1)
        log(f"SOL price: ${sol_price:.4f}")
    except Exception as e:
        log(f"ERROR fetching SOL price: {e}")
        sys.exit(1)

    # 2. Fetch pump.fun top runners
    top_runners = fetch_pumpfun_top_runners(limit=20)
    log(f"pump.fun top-runners: {len(top_runners)} tokens")

    # 3. Fetch DexScreener for those mints
    mints = [t["mint"] for t in top_runners if t.get("mint")]
    dex_data = fetch_dexscreener_for_mints(mints)
    log(f"DexScreener: {len(dex_data)} pairs")

    # 4. Build watchlist snapshot for the dashboard
    watchlist_state = build_watchlist_state(sol_price, top_runners, dex_data)
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps(watchlist_state, indent=2, ensure_ascii=False))

    # 5. Compute portfolio value
    portfolio = compute_portfolio_value(state, sol_price, dex_data)
    log(f"Portfolio: {portfolio}")

    # 6. Update state with portfolio value + timestamp
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    state["last_sol_price_usd"] = sol_price
    state["portfolio_value_usd"] = portfolio["total_value_usd"]
    state["balance_usd_estimate"] = portfolio["sol_balance_value_usd"]
    if state.get("starting_balance_usd") is None:
        state["starting_balance_usd"] = portfolio["total_value_usd"]

    # 7. Run decision policy
    decision = decide(state, sol_price, watchlist_state)
    log(f"Decision: {decision['action']} | {decision['details']}")

    # 8. Append decision to log
    append_decision(decision)

    # 9. Save state
    save_state(state)
    log(f"State saved to {STATE_PATH}")

    # 10. Commit + push
    git_commit_and_push(STATE_PATH, DECISIONS_PATH)

    log("=== Done ===")


if __name__ == "__main__":
    main()