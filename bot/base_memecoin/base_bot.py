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
MIN_LIQUIDITY_USD = 10000      # require $10k+ liquidity
MIN_VOLUME_24H_USD = 5000      # require $5k+ 24h volume
MIN_PAIR_AGE_MINUTES = 2       # wait 2 min before considering
MAX_PAIR_AGE_MINUTES = 1440    # only tokens <24h old

# === Take profit tiers (Base memecoins can 5-50x) ===
TP_TIER_1_PCT = 100             # 2x — sell 25%
TP_TIER_2_PCT = 300             # 4x — sell 50%  
TP_TIER_3_PCT = 500             # 6x — sell all

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


# === DexScreener API ===
def fetch_base_pairs():
    """Fetch Base chain pairs from DexScreener (search-based, returns top 30 by vol)"""
    url = "https://api.dexscreener.com/latest/dex/search?q=base"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "base-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            pairs = data.get("pairs", [])
            # Filter to Base chain only
            return [p for p in pairs if p.get("chainId") == "base"]
    except Exception as e:
        log(f"DexScreener error: {e}")
        return []


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
    sym = pair.get("baseToken", {}).get("symbol", "?")
    addr = pair.get("baseToken", {}).get("address", "?")
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
    
    # Buy decision: simple scoring
    score = 0
    reasons = []
    
    # Positive signals
    if vol > 50000: score += 1; reasons.append("high vol")
    if liq > 50000: score += 1; reasons.append("deep liquidity")
    if buys > sells: score += 1; reasons.append("buy pressure")
    if age < 60: score += 1; reasons.append("fresh")
    if mcap > 0 and mcap < 500000: score += 1; reasons.append("micro-cap")
    if fdv > 0 and fdv < 2000000: score += 1; reasons.append("low FDV = upside")
    
    # Negative signals
    if sells > buys * 2: score -= 2; reasons.append("sell pressure")
    if chg24 < -50: score -= 2; reasons.append("dropping")
    if "pump" in sym.lower() and len(sym) < 6: score -= 1; reasons.append("generic pump name")
    
    if score < 2:
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
        "amount_eth": pos_value_eth,
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
        log(f"  Can\'t get current price for {pos['symbol']}, skipping sell")
        return
    
    entry_price = pos["entry_price_usd"]
    pnl_pct = ((cur_price / entry_price) - 1) * 100
    
    # Realistic slippage simulation
    pos_value_usd = pos["amount_eth"] * 3000  # rough ETH price
    if cur_liq < pos_value_usd * 2:
        # Ghost exit - pool too small
        actual_exit_price = cur_price * 0.1  # 90% slippage
        log(f"  GHOST EXIT ${pos['symbol']} — pool ${cur_liq:.0f} < 2x pos ${pos_value_usd:.0f}")
    elif cur_liq < pos_value_usd:
        actual_exit_price = cur_price * 0.5  # 50% slippage
    else:
        actual_exit_price = cur_price
    
    sol_received_eth = (pos["amount_eth"] * fraction) * (actual_exit_price / entry_price)
    
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
    
    # Update prices for held positions
    held_prices = {}
    for key, pos in state["positions"].items():
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
