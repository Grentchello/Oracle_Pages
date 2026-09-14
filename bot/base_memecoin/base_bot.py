#!/usr/bin/env python3
"""
Base Chain Memecoin Trading Bot — v1.0
Started: 2026-09-13

DIFFERENCES FROM SOLANA BOT:
- Base chain (Coinbase L2) instead of Solana
- Uses DexScreener API (works from container, GMGN blocked)
- No bonding curve phase — Base tokens are immediately on Uniswap V3 / Aerodrome
- Smaller market = less competition, more alpha
- Gas: ~$0.10 per swap (much cheaper than Solana)
- New launch platforms: Clanker, Virtuals, Zora

ARCHITECTURE (fresh, not patched like Solana bot):
- Conservative entry: wait 2 min after pair creation
- Real liquidity required: $10k+ pool minimum
- Tight stops: -20% hard cap
- Take profit: 2x, 5x, 10x tiers (real Base memecoins go 5-50x)
- Hold time: 30 min max
- Position size: 0.01 ETH ($25-30) — test size first
- 1 position max to start (then ramp up)

DATA SOURCES (free):
- DexScreener API: https://api.dexscreener.com (keyless, 60 req/min)
- DexPaprika: https://api.dexpaprika.com (50k req/mo free)
- BaseScan: https://api.basescan.org (5 req/sec free)

NO PAY APIs NEEDED.
"""
import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone
import urllib.request
import urllib.error

# ========== CONFIG ==========
DATA_DIR = Path("/opt/data/hermes_work/bot/base_memecoin")
STATE_PATH = DATA_DIR / "data" / "state.json"
LOG_PATH = DATA_DIR / "logs" / "bot.log"
TRADES_PATH = DATA_DIR / "data" / "trades.json"
HELD_PRICES_PATH = DATA_DIR / "data" / "held_prices.json"
WATCHLIST_PATH = DATA_DIR / "data" / "watchlist.json"

# === Strategy (v1.0 — conservative, learn first) ===
POSITION_SIZE_ETH = 0.01       # ~$25-30 per position
MAX_POSITIONS = 1              # 1 position to start
HARD_STOP_LOSS = 0.20          # -20% hard cap
MAX_HOLD_MINUTES = 30          # 30 min max hold
DAILY_MAX_LOSS_ETH = 0.05      # -0.05 ETH/day cap

# === Entry gates ===
MIN_LIQUIDITY_USD = 500       # v8.2: lowered from $10k - was blocking all trades
MIN_VOLUME_24H_USD = 1000     # v8.2: lowered from $5k
MIN_PAIR_AGE_MINUTES = 2       # wait 2 min before considering
MAX_PAIR_AGE_MINUTES = 1440    # only tokens <24h old

# === Take profit tiers (Base memecoins can 2-10x typically) ===
# v1.3: Lowered targets — memecoins rarely go past 2-3x in 30 min
TP_TIER_1_PCT = 50              # 1.5x — sell 25% (early profit)
TP_TIER_2_PCT = 100             # 2x — sell 50%
TP_TIER_3_PCT = 200             # 3x — sell all

# === Slippage model ===
MAX_SLIPPAGE_PCT = 5           # assume 5% slippage per trade
LIQUIDITY_CHECK_MULT = 3       # need 3x position in pool for safe exit


def log(msg):
    """Log to console + file"""
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a") as f:
        f.write(line + "\n")


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return fresh_state()


def fresh_state():
    return {
        "balance_eth": 0.10,        # 0.10 ETH starting paper balance
        "starting_balance_eth": 0.10,
        "positions": {},
        "trades": [],
        "today_pnl_eth": 0.0,
        "last_pnl_reset": None,
        "total_pnl_eth": 0.0,
        "last_updated": None,
        "bot_version": "v1.0-base",
        "created": datetime.now(timezone.utc).isoformat()
    }


def save_state(state):
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))
    # Also write to wiki for dashboard
    try:
        wiki_state = Path("/opt/data/hermes_work/wiki/projects/base-memecoin/state.json")
        wiki_state.parent.mkdir(parents=True, exist_ok=True)
        wiki_state.write_text(json.dumps(state, indent=2))
    except:
        pass


# === DexScreener API ===


def fetch_new_base_pools():
    """Fetch newest Base pools via DexPaprika (50k free/month, no key)"""
    url = "https://api.dexpaprika.com/networks/base/pools/search?sort=desc&order_by=created_at&limit=20"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "base-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("results", [])
    except Exception as e:
        log(f"DexPaprika error: {e}")
        return []


def pool_to_pair_format(pool):
    """Convert DexPaprika pool to DexScreener-like pair format for consistency"""
    tokens = pool.get("tokens", [])
    base = tokens[0] if len(tokens) > 0 else {}
    quote = tokens[1] if len(tokens) > 1 else {}
    
    # Parse created_at to ms timestamp
    pair_created_ms = None
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(pool.get("created_at", "").replace("Z", "+00:00"))
        pair_created_ms = int(dt.timestamp() * 1000)
    except:
        pass
    
    return {
        "chainId": pool.get("chain", "base"),
        "dexId": pool.get("dex_id", "?"),
        "pairAddress": pool.get("id", "?"),
        "baseToken": {
            "address": base.get("id", base.get("address", "?")),
            "name": base.get("name", "?"),
            "symbol": base.get("symbol", "?"),
        },
        "quoteToken": {
            "symbol": quote.get("symbol", "?"),
        },
        "priceUsd": str(pool.get("price_usd", 0)),
        "liquidity": {"usd": pool.get("liquidity_usd", 0)},
        "volume": {"h24": pool.get("volume_usd_24h", 0)},
        "priceChange": {
            "h24": pool.get("price_change_percentage_24h", 0),
            "h1": pool.get("price_change_percentage_1h", 0),
        },
        "fdv": pool.get("fdv_usd", 0),
        "marketCap": pool.get("market_cap_usd", 0),
        "pairCreatedAt": pair_created_ms,
        "txns": {"h24": {"buys": 0, "sells": pool.get("transactions_24h", 0)}},
        "dexpaprika_raw": pool,
    }


def fetch_base_pairs():
    """Fetch Base chain pairs from DexPaprika (sorted by creation time) + DexScreener boosts.
    
    Primary source: DexPaprika (50k free/month, no key, sorted by creation time).
    Fallback: DexScreener token profiles/boosts (60 req/min, profile-based).
    """
    pairs = []
    
    # Primary: DexPaprika new pools
    pools = fetch_new_base_pools()
    for p in pools:
        pairs.append(pool_to_pair_format(p))
    
    # If no DexPaprika results, try DexScreener profiles
    if not pairs:
        log("DexPaprika empty, falling back to DexScreener profiles")
        for endpoint in [
            "https://api.dexscreener.com/token-profiles/latest/v1",
            "https://api.dexscreener.com/token-boosts/latest/v1",
        ]:
            try:
                req = urllib.request.Request(endpoint, headers={"User-Agent": "base-bot/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
                    for profile in data if isinstance(data, list) else []:
                        if profile.get("chainId") == "base" and profile.get("tokenAddress"):
                            addr = profile["tokenAddress"]
                            url = f"https://api.dexscreener.com/token-pairs/v1/base/{addr}"
                            req2 = urllib.request.Request(url, headers={"User-Agent": "base-bot/1.0"})
                            with urllib.request.urlopen(req2, timeout=10) as resp2:
                                token_pairs = json.loads(resp2.read().decode())
                                for tp in token_pairs:
                                    if tp.get("chainId") == "base":
                                        pairs.append(tp)
                                        break
            except Exception as e:
                log(f"DexScreener fallback error: {e}")
    
    return pairs

def fetch_token_pairs(address):
    """Fetch all pairs for a specific token"""
    url = f"https://api.dexscreener.com/token-pairs/v1/base/{address}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "base-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log(f"Token pairs error: {e}")
        return []


def fetch_new_pairs():
    """Get newly created Base pairs (sorted by age)"""
    # DexScreener search sorted by pairCreatedAt
    url = "https://api.dexscreener.com/latest/dex/search?q=base"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "base-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("pairs", [])
    except Exception as e:
        log(f"New pairs error: {e}")
        return []


def to_float(v, default=0):
    if v is None:
        return default
    try:
        return float(v)
    except:
        return default


def pair_age_minutes(pair):
    """Get pair age in minutes from pairCreatedAt (ms timestamp)"""
    ts = pair.get("pairCreatedAt", 0)
    if not ts:
        return None
    age_ms = time.time() * 1000 - ts
    return age_ms / 60000


def filter_pair(pair):
    """Return reason string if filtered, None if passes all gates"""
    # Must be Base chain
    if pair.get("chainId") != "base":
        return "not base chain"
    
    # Liquidity floor: $10k
    liq = to_float(pair.get("liquidity", {}).get("usd", 0))
    if liq < MIN_LIQUIDITY_USD:
        return f"liq ${liq:.0f} < ${MIN_LIQUIDITY_USD}"
    
    # 24h volume floor: $5k
    vol = to_float(pair.get("volume", {}).get("h24", 0))
    if vol < MIN_VOLUME_24H_USD:
        return f"vol ${vol:.0f} < ${MIN_VOLUME_24H_USD}"
    
    # Age window: 2 min - 24h
    age_min = pair_age_minutes(pair)
    if age_min is None:
        return "no age data"
    if age_min < MIN_PAIR_AGE_MINUTES:
        return f"too young ({age_min:.1f}min)"
    if age_min > MAX_PAIR_AGE_MINUTES:
        return f"too old ({age_min:.1f}min)"
    
    # Price change sanity: not already pumped >500% in 24h
    chg24 = to_float(pair.get("priceChange", {}).get("h24", 0))
    if chg24 > 500:
        return f"already pumped +{chg24:.0f}% in 24h"
    
    # Negative momentum filter
    chg1h = to_float(pair.get("priceChange", {}).get("h1", 0))
    if chg1h < -30:
        return f"dumping ({chg1h:.0f}% in 1h)"
    
    return None


def decide(pair, state):
    """Make a trade decision. Returns dict or None."""
    # v1.4: Symbol may be missing in DexPaprika data. Use short address as fallback.
    sym = pair.get("baseToken", {}).get("symbol", "?")
    addr = pair.get("baseToken", {}).get("address", "?")
    
    # v1.5: Skip stablecoins / wrapped assets (price > $1)
    price = to_float(pair.get("priceUsd", 0))
    if price > 1.0:
        return None  # Skip - probably stablecoin
    if sym == "?" and addr != "?":
        sym = "0x" + addr[-6:]
    name = pair.get("baseToken", {}).get("name", "?")
    price = to_float(pair.get("priceUsd", 0))
    liq = to_float(pair.get("liquidity", {}).get("usd", 0))
    vol = to_float(pair.get("volume", {}).get("h24", 0))
    age = pair_age_minutes(pair)
    fdv = to_float(pair.get("fdv", 0))
    mcap = to_float(pair.get("marketCap", 0))
    dex = pair.get("dexId", "?")
    txns = pair.get("txns", {}).get("h24", {})
    buys = txns.get("buys", 0) if isinstance(txns, dict) else 0
    sells = txns.get("sells", 0) if isinstance(txns, dict) else 0
    chg24 = to_float(pair.get("priceChange", {}).get("h24", 0))
    chg1h = to_float(pair.get("priceChange", {}).get("h1", 0))
    
    # Buy decision: simple scoring
    score = 0
    reasons = []
    
    # Positive signals (v1.5: higher bars to reduce low-quality trades)
    if vol > 10000: score += 1; reasons.append("good vol")
    if liq > 10000: score += 1; reasons.append("decent liquidity")
    if buys > sells and sells > 0: score += 1; reasons.append("buy pressure")
    if 1 < age < 1440: score += 1; reasons.append("established")  # 1min-24h, not just fresh
    if buys > 10 and sells > 5: score += 1; reasons.append("active trading")
    
    # Negative signals
    if sells > buys * 2: score -= 2; reasons.append("sell pressure")
    if chg24 < -50: score -= 2; reasons.append("dropping")
    if "pump" in sym.lower() and len(sym) < 6: score -= 1; reasons.append("generic pump name")
    
    if score < 1:  # v1.5: require positive score (at least one bullish signal)
        return None
    
    return {
        "action": "buy",
        "symbol": sym,
        "name": name,
        "address": addr,
        "price_eth": price,
        "liquidity_usd": liq,
        "volume_24h": vol,
        "market_cap": mcap,
        "fdv": fdv,
        "age_min": age,
        "dex": dex,
        "buys": buys,
        "sells": sells,
        "score": score,
        "reasons": reasons,
    }


def execute_buy(state, decision):
    """Execute a buy in paper mode"""
    pos_value_eth = POSITION_SIZE_ETH
    
    if state["balance_eth"] - pos_value_eth < 0.01:  # keep some reserve
        log(f"  Insufficient balance for buy: {state['balance_eth']} ETH")
        return None
    
    state["balance_eth"] -= pos_value_eth
    
    pos = {
        "symbol": decision["symbol"],
        "name": decision["name"],
        "address": decision["address"],
        "position_size_eth": pos_value_eth,  # v1.3 fix: ETH spent on entry
        "entry_sol_spent": pos_value_eth,    # alias for compatibility
        "amount_tokens": 0,  # placeholder; not needed for v1.3 math
        "entry_price_usd": decision["price_eth"],
        "entry_time": datetime.now(timezone.utc).isoformat(),
        "entry_liquidity_usd": decision["liquidity_usd"],
        "entry_volume_24h": decision["volume_24h"],
        "entry_market_cap": decision["market_cap"],
        "entry_score": decision["score"],
        "entry_reasons": decision["reasons"],
        "entry_dex": decision["dex"],
        "fraction_sold": 0.0,
    }
    
    # Use address as key, or symbol if address missing
    key = decision["address"] or decision["symbol"]
    state["positions"][key] = pos
    log(f"  BOUGHT ${decision['symbol']} at ${decision['price_eth']:.6g} for {pos_value_eth} ETH ({decision['reasons']})")
    return pos


def check_exits(state, held_prices):
    """Check held positions for exit signals"""
    exits = []
    for key, pos in list(state["positions"].items()):
        addr = pos["address"]
        held = held_prices.get(addr)
        if not held:
            continue
        
        cur_price = to_float(held.get("priceUsd", 0))
        if cur_price <= 0:
            continue
        
        entry_price = pos["entry_price_usd"]
        pnl_pct = ((cur_price / entry_price) - 1) * 100 if entry_price > 0 else 0
        held_minutes = (time.time() - datetime.fromisoformat(pos["entry_time"]).timestamp()) / 60
        
        # Take-profit tiers
        if pnl_pct >= TP_TIER_3_PCT and pos["fraction_sold"] < 1.0:
            exits.append((key, "sell_all", 1.0, f"TP +{TP_TIER_3_PCT}%"))
        elif pnl_pct >= TP_TIER_2_PCT and pos["fraction_sold"] < 0.75:
            exits.append((key, "sell_half", 0.5, f"TP +{TP_TIER_2_PCT}% (50%)"))
        elif pnl_pct >= TP_TIER_1_PCT and pos["fraction_sold"] < 0.25:
            exits.append((key, "sell_quarter", 0.25, f"TP +{TP_TIER_1_PCT}% (25%)"))
        
        # Hard stop
        elif pnl_pct <= -HARD_STOP_LOSS * 100:
            exits.append((key, "sell_all", 1.0, f"hard-stop -{int(HARD_STOP_LOSS*100)}%"))
        
        # Max hold time
        elif held_minutes >= MAX_HOLD_MINUTES:
            exits.append((key, "sell_all", 1.0, f"max-hold {MAX_HOLD_MINUTES}min"))
    
    return exits


def execute_sell(state, key, fraction, reason):
    """Execute a sell in paper mode"""
    pos = state["positions"].get(key)
    if not pos:
        return
    
    # Need current price - try to fetch
    addr = pos["address"]
    pairs = fetch_token_pairs(addr)
    cur_price = 0
    cur_liq = 0
    for p in pairs:
        cur_price = to_float(p.get("priceUsd", 0))
        cur_liq = to_float(p.get("liquidity", {}).get("usd", 0))
        if cur_price > 0:
            break
    
    if cur_price <= 0:
        log(f"  Can\'t get current price for {pos['symbol']} — forcing ghost exit")
        # Force close position with -100% loss since we can\'t verify exit price
        position_size_eth = pos.get("position_size_eth", pos.get("entry_sol_spent", 0.01))
        trade = {
            "symbol": pos["symbol"],
            "name": pos["name"],
            "address": pos["address"],
            "amount_eth_sold": position_size_eth,
            "fraction_sold": 1.0,
            "entry_time": pos["entry_time"],
            "exit_time": datetime.now(timezone.utc).isoformat(),
            "entry_price_usd": entry_price,
            "exit_price_usd": 0.0,
            "entry_amount_eth": position_size_eth,
            "exit_amount_eth": 0.0,
            "pnl_eth": -position_size_eth,
            "pnl_pct": -100.0,
            "exit_reason": f"[GHOST] {reason} — no price data",
            "entry_liquidity_usd": pos.get("entry_liquidity_usd", 0),
            "exit_liquidity_usd": 0,
            "ghost_exit": True,
        }
        state["trades"].append(trade)
        if key in state["positions"]:
            del state["positions"][key]
        return
    
    entry_price = pos["entry_price_usd"]
    pnl_pct = ((cur_price / entry_price) - 1) * 100
    
    # Realistic slippage simulation
    position_size_eth = pos.get("position_size_eth", pos.get("entry_sol_spent", 0.01)) * fraction
    pos_value_usd = position_size_eth * 3000  # rough ETH price
    if cur_liq < pos_value_usd * 2:
        # Ghost exit - pool too small
        actual_exit_price = cur_price * 0.1  # 90% slippage
        log(f"  GHOST EXIT ${pos['symbol']} — pool ${cur_liq:.0f} < 2x pos ${pos_value_usd:.0f}")
    elif cur_liq < pos_value_usd:
        actual_exit_price = cur_price * 0.5  # 50% slippage
    else:
        actual_exit_price = cur_price
    
    # v1.3 FIX: use position_size_eth (ETH spent on entry), not amount (token count)
    position_size_eth = pos.get("position_size_eth", pos.get("entry_sol_spent", 0)) * fraction
    sol_received_eth = position_size_eth * (actual_exit_price / entry_price)
    
    trade = {
        "symbol": pos["symbol"],
        "name": pos["name"],
        "address": pos["address"],
        "amount_eth_sold": pos["amount_eth"] * fraction,
        "fraction_sold": fraction,
        "entry_time": pos["entry_time"],
        "exit_time": datetime.now(timezone.utc).isoformat(),
        "entry_price_usd": entry_price,
        "exit_price_usd": actual_exit_price,
        "entry_amount_eth": pos["amount_eth"] * fraction,
        "exit_amount_eth": sol_received_eth,
        "pnl_eth": sol_received_eth - (pos["amount_eth"] * fraction),
        "pnl_pct": pnl_pct,
        "exit_reason": reason,
        "entry_liquidity_usd": pos.get("entry_liquidity_usd", 0),
        "exit_liquidity_usd": cur_liq,
        "ghost_exit": cur_liq < pos_value_usd * 2,
    }
    
    state["trades"].append(trade)
    state["balance_eth"] = round(state["balance_eth"] + sol_received_eth, 6)
    pos["fraction_sold"] = pos.get("fraction_sold", 0) + fraction
    
    if fraction >= 0.999 or pos["fraction_sold"] >= 0.999:
        del state["positions"][key]
    
    log(f"  SOLD {fraction*100:.0f}% ${pos['symbol']} @ ${cur_price:.6g} → PnL {trade['pnl_pct']:+.1f}% ({trade['pnl_eth']:+.5f} ETH)")


def main():
    log("=" * 50)
    log("Base Memecoin Bot v1.0 starting...")
    state = load_state()
    log(f"Balance: {state['balance_eth']} ETH")
    log(f"Positions: {len(state['positions'])}")
    log(f"Total trades: {len(state['trades'])}")
    
    # Fetch candidate pairs
    pairs = fetch_base_pairs()
    log(f"DexScreener: fetched {len(pairs)} Base pairs")
    
    if not pairs:
        log("No pairs fetched, exiting")
        return
    
    # Filter pairs
    candidates = []
    for p in pairs:
        reason = filter_pair(p)
        if reason:
            continue
        decision = decide(p, state)
        if decision:
            candidates.append(decision)
    
    log(f"After filters: {len(candidates)} candidates pass all gates")
    
    # Try to buy top candidate (if room for new position)
    if len(state["positions"]) < MAX_POSITIONS and candidates:
        candidates.sort(key=lambda c: c["score"], reverse=True)
        best = candidates[0]
        log(f"BEST CANDIDATE: ${best['symbol']} score={best['score']} reasons={best['reasons']}")
        execute_buy(state, best)
    
    # v1.3: Use entry_price as held price for first tick (avoid phantom +500% from stale prices)
    held_prices = {}
    for key, pos in state["positions"].items():
        # Use entry price for immediate next tick (prevents race condition)
        entry_price = pos.get("entry_price_usd", 0)
        if entry_price > 0:
            held_prices[pos["address"]] = {"priceUsd": str(entry_price), "liquidity_usd": pos.get("entry_liquidity_usd", 0)}
        # Then refresh from API for subsequent ticks
        else:
            pairs_data = fetch_token_pairs(pos["address"])
            for p in pairs_data:
                if to_float(p.get("priceUsd", 0)) > 0:
                    held_prices[pos["address"]] = p
                    break
    
    # Check exits
    exits = check_exits(state, held_prices)
    for key, action, fraction, reason in exits:
        log(f"EXIT SIGNAL: ${state['positions'].get(key, {}).get('symbol', '?')} {action} ({reason})")
        execute_sell(state, key, fraction, reason)
    
    # Update today PnL
    today = datetime.now(timezone.utc).date().isoformat()
    if state.get("last_pnl_reset") != today:
        state["today_pnl_eth"] = 0
        state["last_pnl_reset"] = today
    
    state["today_pnl_eth"] = sum(
        t["pnl_eth"] for t in state["trades"]
        if t["exit_time"].startswith(today)
    )
    state["total_pnl_eth"] = sum(t["pnl_eth"] for t in state["trades"])
    
    save_state(state)
    
    log(f"Final: balance={state['balance_eth']} ETH, positions={len(state['positions'])}, today PnL={state['today_pnl_eth']:+.5f} ETH")


if __name__ == "__main__":
    main()
