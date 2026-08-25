#!/usr/bin/env python3
"""
Memecoin Trading Bot — Phase 2

Fetches real Solana prices + pump.fun trending tokens, maintains a paper
portfolio with 2 SOL, takes positions on momentum signals, closes them per
take-profit / stop-loss / time-stop / slot-pressure rules.

Run from this script's directory:
    python3 bot.py
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# === Paths ===
SCRIPT_DIR = Path(__file__).parent.resolve()
WORK_DIR = SCRIPT_DIR.parent
WIKI_DIR = WORK_DIR / "wiki"
STATE_PATH = WIKI_DIR / "trading" / "state.json"
DECISIONS_PATH = WIKI_DIR / "trading" / "decisions.md"
WATCHLIST_PATH = WIKI_DIR / "trading" / "watchlist.json"
TRADES_PATH = WIKI_DIR / "trading" / "trades.json"

# === APIs ===
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
PUMPFUN_TOP_RUNNERS = "https://frontend-api-v3.pump.fun/coins/top-runners"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# === Strategy parameters ===
POSITION_SIZE_SOL = 0.1          # SOL per entry
MAX_POSITIONS = 5                # max concurrent positions
MIN_LIQUIDITY_USD = 5000         # skip tokens with less liquidity
MIN_VOLUME_24H_USD = 10000       # skip tokens with less 24h volume
MIN_PRICE_CHANGE_24H = 0.0       # skip if 24h change is negative
TAKE_PROFIT_MULT = 1.30          # sell HALF at +30% (partial TP)
TAKE_PROFIT_FULL_MULT = 1.60     # sell remainder at +60%
STOP_LOSS_MULT = 0.80            # sell at -20% (tighter — faster exit on losers)
MAX_HOLD_SECONDS = 12 * 3600     # exit after 12h if neither TP/SL (was 24h)
MOMENTUM_FADE_MIN_PROFIT = 0.15  # exit on momentum fade if ≥+15% profit
PRICE_STALE_SECONDS = 1800       # skip tokens whose last trade is >30min old
MIN_SCORE = 5.0                  # momentum score threshold for entry

# === Daily target ===
DAILY_TARGET_PNL_PCT = 20.0     # % target for paper portfolio in 24h
PARTIAL_TP_FRACTION = 0.5        # sell 50% at first TP

# === Network ===
TIMEOUT = 15
USER_AGENT = "oracle-vault-memecoin-bot/0.2"


# =====================================================================
# Utilities
# =====================================================================

def _to_float(v, default=0.0):
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


def now_utc():
    return datetime.now(timezone.utc)


def iso_now():
    return now_utc().isoformat()


def parse_iso(s):
    if not s:
        return None
    try:
        # Handle trailing Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# =====================================================================
# Data fetchers
# =====================================================================

def fetch_sol_price_usd():
    """SOL price in USD via DexScreener (highest-liquidity Solana pool)."""
    url = f"{DEXSCREENER_BASE}/tokens/{SOL_MINT}"
    data = http_get_json(url)
    pairs = [p for p in (data.get("pairs") or [])
             if p.get("chainId") == "solana" and _to_float(p.get("priceUsd")) > 0]
    if not pairs:
        return None
    pairs.sort(key=lambda p: _to_float((p.get("liquidity") or {}).get("usd")), reverse=True)
    return _to_float(pairs[0]["priceUsd"])


def fetch_pumpfun_top_runners(limit=30):
    """Top trending tokens from pump.fun frontend API (no auth)."""
    try:
        data = http_get_json(PUMPFUN_TOP_RUNNERS)
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
                "market_cap_usd": _to_float(coin.get("usd_market_cap") or coin.get("market_cap_usd")),
                "last_trade_ts": coin.get("last_trade_timestamp"),
                "complete": coin.get("complete", False),  # graduated to PumpSwap/Raydium
                "ath_market_cap_usd": _to_float(coin.get("ath_market_cap")),
                "source": "pump.fun top-runners",
            })
        return out
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log(f"WARN: pump.fun fetch failed: {e}")
        return []


def fetch_dexscreener_for_mints(mints):
    """Fetch DexScreener pair data for a list of mints. Returns mint -> pair."""
    out = {}
    if not mints:
        return out
    try:
        url = f"{DEXSCREENER_BASE}/tokens/{','.join(mints[:30])}"
        data = http_get_json(url)
        for pair in data.get("pairs") or []:
            mint = pair.get("baseToken", {}).get("address")
            if not mint:
                continue
            new_liq = _to_float((pair.get("liquidity") or {}).get("usd"))
            existing = out.get(mint)
            existing_liq = _to_float((existing.get("liquidity") or {}).get("usd")) if existing else 0
            if existing is None or new_liq > existing_liq:
                out[mint] = pair
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
        log(f"WARN: DexScreener fetch failed: {e}")
    return out


# =====================================================================
# State persistence
# =====================================================================

def load_state():
    if not STATE_PATH.exists():
        return _fresh_state()
    try:
        return json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        log("WARN: state.json unreadable, starting fresh")
        return _fresh_state()


def _fresh_state():
    return {
        "balance_sol": 2.0,
        "starting_balance_sol": 2.0,
        "positions": {},      # mint -> {amount, entry_price_usd, entry_time, entry_signals, symbol, name}
        "trades": [],         # closed trades (newest last)
        "bot_version": "0.2.0-trading",
    }


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def save_trades_log(state):
    """Persist trade ledger separately for easy history viewing."""
    TRADES_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRADES_PATH.write_text(json.dumps(state.get("trades", []), indent=2, ensure_ascii=False))


def append_decision(decision):
    """Append a decision line to decisions.md (the human-readable log)."""
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DECISIONS_PATH.exists():
        DECISIONS_PATH.write_text(
            "# Bot Decisions Log\n\n"
            "> Append-only log of every bot decision. Each line is one observation/thought/action.\n"
            "> Format: `## [YYYY-MM-DD HH:MM UTC] <action> | <details>`\n\n"
        )
    ts = now_utc().strftime("%Y-%m-%d %H:%M UTC")
    line = f"## [{ts}] {decision['action']} | {decision['details']}\n"
    if decision.get("reason"):
        line += f"- Reasoning: {decision['reason']}\n"
    if decision.get("data"):
        line += f"- Data: `{json.dumps(decision['data'])}`\n"
    line += "\n"
    with open(DECISIONS_PATH, "a") as f:
        f.write(line)


def load_recent_decisions(max_n=20):
    """Parse last N decisions from decisions.md (for the dashboard bundle)."""
    if not DECISIONS_PATH.exists():
        return []
    text = DECISIONS_PATH.read_text()
    decisions = []
    current = None
    for line in text.splitlines():
        m = re.match(r"^## \[([^\]]+)\] (\S+) \| (.*)$", line)
        if m:
            if current:
                decisions.append(current)
            current = {
                "time": m.group(1),
                "action": m.group(2),
                "details": m.group(3),
                "reason": "",
            }
        elif current:
            rm = re.match(r"^- Reasoning: (.*)$", line)
            if rm:
                current["reason"] = rm.group(1)
    if current:
        decisions.append(current)
    return decisions[-max_n:]


# =====================================================================
# Watchlist + portfolio valuation
# =====================================================================

def build_watchlist_state(sol_price, top_runners, dex_data):
    """Build a watchlist snapshot for the dashboard."""
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
            entry["dex_id"] = pair.get("dexId")
            entry["pair_address"] = pair.get("pairAddress")
        enriched.append(entry)
    return {
        "fetched_at": iso_now(),
        "sol_price_usd": sol_price,
        "tokens": enriched,
    }


def compute_portfolio_value(state, sol_price, dex_data):
    positions_value_usd = 0.0
    for mint, pos in state.get("positions", {}).items():
        pair = dex_data.get(mint)
        if pair and _to_float(pair.get("priceUsd")) > 0:
            positions_value_usd += pos["amount"] * _to_float(pair["priceUsd"])
        elif pos.get("entry_price_usd"):
            # Use entry price as last resort (we still hold it but no live price)
            positions_value_usd += pos["amount"] * pos["entry_price_usd"]
    sol_value = state.get("balance_sol", 0) * sol_price
    total = sol_value + positions_value_usd
    return {
        "sol_balance_value_usd": round(sol_value, 2),
        "positions_value_usd": round(positions_value_usd, 2),
        "total_value_usd": round(total, 2),
    }


# =====================================================================
# Strategy: entry signals
# =====================================================================

def evaluate_entry_signals(token, pair, now):
    """
    Returns (passes: bool, reason: str, score: float, components: dict).

    Scoring (higher = stronger momentum, more likely to enter):
      base          = 24h price change %
      velocity      = how recently the token traded (recency bonus)
      vol_liq_ratio = vol24h / liquidity (turnover intensity)
      mcap_velocity = mcap relative to ATH — recent movers haven't dumped yet
      liquidity_bonus = log(liquidity) — bigger pools are safer

    Score must exceed MIN_SCORE to be entered.
    """
    if not pair:
        return False, "no DexScreener pair data", 0, {}
    price_usd = _to_float(pair.get("priceUsd"))
    if price_usd <= 0:
        return False, "no USD price", 0, {}
    liq = _to_float((pair.get("liquidity") or {}).get("usd"))
    vol24 = _to_float((pair.get("volume") or {}).get("h24"))
    chg24 = _to_float((pair.get("priceChange") or {}).get("h24"))
    chg1h = _to_float((pair.get("priceChange") or {}).get("h1"))
    chg5m = _to_float((pair.get("priceChange") or {}).get("m5"))
    last_trade_ts = token.get("last_trade_ts")
    age_min = None
    if last_trade_ts:
        age_sec = (now.timestamp() * 1000 - last_trade_ts) / 1000
        age_min = age_sec / 60
        if age_sec > PRICE_STALE_SECONDS:
            return False, f"stale price ({age_min:.0f}min old)", 0, {}

    if liq < MIN_LIQUIDITY_USD:
        return False, f"low liquidity ${liq:.0f} < ${MIN_LIQUIDITY_USD}", 0, {}
    if vol24 < MIN_VOLUME_24H_USD:
        return False, f"low 24h volume ${vol24:.0f} < ${MIN_VOLUME_24H_USD}", 0, {}
    if chg24 < MIN_PRICE_CHANGE_24H:
        return False, f"negative 24h change {chg24:.1f}%", 0, {}

    # Velocity — fresh trades = active token
    recency_bonus = 0
    if age_min is not None:
        if age_min < 5:
            recency_bonus = 10      # actively trading right now
        elif age_min < 30:
            recency_bonus = 5
        elif age_min < 120:
            recency_bonus = 2

    # Vol/liq ratio — high turnover = real interest (cap to avoid absurd scores)
    vol_liq_ratio = (vol24 / liq) if liq > 0 else 0
    turnover_bonus = min(vol_liq_ratio * 3, 15)  # cap at 15

    # Recent momentum — 1h and 5m changes (very aggressive boost if pumping hard now)
    short_momentum = max(chg1h * 0.5, chg5m * 2) if chg1h is not None or chg5m is not None else 0

    score = chg24 + recency_bonus + turnover_bonus + short_momentum

    components = {
        "chg24": chg24,
        "chg1h": chg1h,
        "chg5m": chg5m,
        "liquidity_usd": liq,
        "volume_24h_usd": vol24,
        "vol_liq_ratio": round(vol_liq_ratio, 2),
        "recency_min": round(age_min, 1) if age_min else None,
        "score_breakdown": {
            "base_24h": chg24,
            "recency_bonus": recency_bonus,
            "turnover_bonus": round(turnover_bonus, 1),
            "short_momentum": round(short_momentum, 1),
            "total": round(score, 1),
        }
    }

    if score < MIN_SCORE:
        return False, f"score {score:.1f} below threshold {MIN_SCORE}", score, components

    return True, "all gates passed", score, components


def find_entry_candidate(state, watchlist, now):
    """Return (mint, signal_data) for the best entry, or (None, reason)."""
    held_mints = set(state.get("positions", {}).keys())
    available_slots = MAX_POSITIONS - len(held_mints)
    if available_slots <= 0:
        return None, "max positions held"
    if state.get("balance_sol", 0) < POSITION_SIZE_SOL:
        return None, f"insufficient SOL ({state.get('balance_sol', 0):.3f} < {POSITION_SIZE_SOL})"

    best = None
    best_score = -1e9
    best_reason = ""
    best_token = None
    best_components = {}
    considered = 0

    for token in watchlist.get("tokens", []):
        mint = token.get("mint")
        if not mint or mint in held_mints:
            continue
        pair = {
            "priceUsd": token.get("price_usd"),
            "liquidity": {"usd": token.get("liquidity_usd")},
            "volume": {"h24": token.get("volume_h24")},
            "priceChange": {"h24": token.get("price_change_h24")},
        }
        passes, reason, score, components = evaluate_entry_signals(token, pair, now)
        considered += 1
        if not passes:
            continue
        if score > best_score:
            best = mint
            best_score = score
            best_reason = reason
            best_token = token
            best_components = components

    if best is None:
        return None, f"no candidate passed gates (considered {considered})"
    return best, {"reason": best_reason, "score": best_score, "token": best_token, "components": best_components}


# =====================================================================
# Strategy: exit signals
# =====================================================================

def evaluate_exit(position, current_price_usd, current_change_24h, now):
    """
    Return (should_exit: bool, reason: str, pnl_pct: float, action: str, fraction: float).

    action: 'full' = sell all, 'partial' = sell PARTIAL_TP_FRACTION
    """
    entry_price = position["entry_price_usd"]
    if not entry_price or current_price_usd is None:
        return False, "no price data", 0.0, "hold", 0.0

    pnl_mult = current_price_usd / entry_price
    pnl_pct = (pnl_mult - 1.0) * 100.0

    # Has this position already taken a partial profit?
    partial_taken = position.get("partial_tp_taken", False)

    # Full take-profit on the remaining position
    if partial_taken and pnl_mult >= TAKE_PROFIT_FULL_MULT:
        return True, f"full-take-profit (+{(pnl_mult-1)*100:.1f}%)", pnl_pct, "full", 1.0

    # First partial take-profit
    if not partial_taken and pnl_mult >= TAKE_PROFIT_MULT:
        return True, f"partial-take-profit (+{(pnl_mult-1)*100:.1f}%)", pnl_pct, "partial", PARTIAL_TP_FRACTION

    # Stop loss — always full exit
    if pnl_mult <= STOP_LOSS_MULT:
        return True, f"stop-loss ({(pnl_mult-1)*100:.1f}%)", pnl_pct, "full", 1.0

    # Time stop
    entry_time = parse_iso(position.get("entry_time"))
    if entry_time:
        held_for = (now - entry_time).total_seconds()
        if held_for >= MAX_HOLD_SECONDS:
            return True, f"time-stop ({held_for/3600:.1f}h held)", pnl_pct, "full", 1.0

    # Momentum fade — exit if 24h change has flipped negative AND we're in profit
    if current_change_24h is not None and current_change_24h < 0 and pnl_pct >= MOMENTUM_FADE_MIN_PROFIT * 100:
        return True, f"momentum-fade (+{pnl_pct:.1f}% locked, 24h now {current_change_24h:.1f}%)", pnl_pct, "full", 1.0

    return False, "hold", pnl_pct, "hold", 0.0


# =====================================================================
# Trade execution (paper)
# =====================================================================

def execute_buy(state, mint, token, price_usd, now):
    """Open a new position, debit SOL balance."""
    sol_cost = POSITION_SIZE_SOL
    token_amount = sol_cost / (price_usd / _to_float(state.get("last_sol_price_usd", price_usd)))
    # Simpler: token_amount in token units, valued in USD at entry
    # Actually we want: amount = how many tokens we got with `sol_cost` SOL
    # At SOL price `sol_price` per SOL, that's `sol_cost * sol_price` USD
    # At token price `price_usd` per token, that's `sol_cost * sol_price / price_usd` tokens
    sol_price_usd = _to_float(state.get("last_sol_price_usd", 0))
    if sol_price_usd <= 0:
        sol_price_usd = price_usd  # fallback shouldn't happen
    usd_value = sol_cost * sol_price_usd
    token_amount = usd_value / price_usd if price_usd > 0 else 0

    if token_amount <= 0:
        return False, "could not size position (price 0)"

    if state.get("balance_sol", 0) < sol_cost:
        return False, f"insufficient SOL ({state.get('balance_sol'):.3f} < {sol_cost})"

    position = {
        "symbol": token.get("symbol", "?"),
        "name": token.get("name", "?"),
        "amount": token_amount,
        "entry_price_usd": price_usd,
        "entry_sol_spent": sol_cost,
        "entry_time": iso_now(),
        "entry_usd_value": usd_value,
        "entry_signals": {
            "liquidity_usd": token.get("liquidity_usd"),
            "volume_h24": token.get("volume_h24"),
            "price_change_h24": token.get("price_change_h24"),
            "market_cap_usd": token.get("market_cap_usd"),
        },
    }
    state["positions"][mint] = position
    state["balance_sol"] = round(state.get("balance_sol", 0) - sol_cost, 6)
    return True, position


def execute_sell(state, mint, price_usd, reason, now, fraction=1.0,
                exit_signals=None, holding_seconds=None):
    """
    Close a position (full or partial), credit SOL balance, append to trades ledger.
    For partial sells, the position stays open with reduced amount.

    fraction: 1.0 = sell all, 0.5 = sell half (leaves rest open)
    exit_signals: dict with current market data at exit (for post-mortem)
    """
    pos = state["positions"].get(mint)
    if not pos:
        return False, "no such position"

    sol_price_usd = _to_float(state.get("last_sol_price_usd", 0))

    # Compute sell amount based on fraction
    total_amount = pos["amount"]
    sell_amount = total_amount * fraction
    remaining_amount = total_amount - sell_amount

    usd_value_at_exit = sell_amount * price_usd
    sol_proceeds = usd_value_at_exit / sol_price_usd if sol_price_usd > 0 else 0

    # For PnL attribution, split the original entry cost proportionally
    entry_sol_total = pos["entry_sol_spent"]
    entry_sol_for_this_chunk = entry_sol_total * fraction
    pnl_sol = sol_proceeds - entry_sol_for_this_chunk
    pnl_pct = (price_usd / pos["entry_price_usd"] - 1.0) * 100.0 if pos["entry_price_usd"] > 0 else 0.0

    trade = {
        "mint": mint,
        "symbol": pos.get("symbol", "?"),
        "name": pos.get("name", "?"),
        "amount_sold": sell_amount,
        "fraction_sold": fraction,
        "entry_time": pos.get("entry_time"),
        "exit_time": iso_now(),
        "entry_price_usd": pos["entry_price_usd"],
        "exit_price_usd": price_usd,
        "entry_sol_for_chunk": round(entry_sol_for_this_chunk, 6),
        "exit_sol_received": round(sol_proceeds, 6),
        "pnl_sol": round(pnl_sol, 6),
        "pnl_pct": round(pnl_pct, 2),
        "exit_reason": reason,
        "entry_signals": pos.get("entry_signals", {}),
        "exit_signals": exit_signals or {},
        "holding_seconds": holding_seconds,
        "partial": fraction < 1.0,
        "post_mortem": generate_post_mortem(pos, price_usd, reason, exit_signals, holding_seconds, fraction),
    }
    state["trades"].append(trade)
    state["balance_sol"] = round(state.get("balance_sol", 0) + sol_proceeds, 6)

    if fraction >= 0.999:
        # Full exit — remove position
        del state["positions"][mint]
    else:
        # Partial exit — update remaining amount + mark partial TP taken
        pos["amount"] = remaining_amount
        pos["partial_tp_taken"] = True
        pos["entry_sol_spent"] = entry_sol_total * (1 - fraction)  # remaining cost basis

    return True, trade


def generate_post_mortem(position, exit_price, exit_reason, exit_signals, holding_seconds, fraction):
    """
    Generate a structured post-mortem explaining why this trade performed as it did.
    Compares entry signals to exit signals to identify what changed.
    """
    entry_signals = position.get("entry_signals", {})
    entry_price = position["entry_price_usd"]
    pnl_pct = (exit_price / entry_price - 1) * 100 if entry_price > 0 else 0

    # What we thought vs what happened
    entry_chg = entry_signals.get("price_change_h24", "?")
    exit_chg = exit_signals.get("price_change_h24", "?")
    entry_liq = entry_signals.get("liquidity_usd", "?")
    exit_liq = exit_signals.get("liquidity_usd", "?")
    entry_vol = entry_signals.get("volume_h24", "?")
    exit_vol = exit_signals.get("volume_h24", "?")

    diagnosis_parts = []
    if pnl_pct > 0:
        diagnosis_parts.append(f"WIN — captured +{pnl_pct:.1f}% via {exit_reason}")
    else:
        diagnosis_parts.append(f"LOSS — exited at {pnl_pct:.1f}% via {exit_reason}")

    # Was our entry thesis correct?
    if entry_chg != "?" and exit_chg != "?":
        try:
            if float(entry_chg) > 20 and pnl_pct > 0:
                diagnosis_parts.append("high-momentum entry thesis worked")
            elif float(entry_chg) > 20 and pnl_pct < 0:
                diagnosis_parts.append("HIGH-MOMENTUM BUT REVERSED — entered too late, smart money already exiting")
            elif float(entry_chg) < 10 and pnl_pct < 0:
                diagnosis_parts.append("weak momentum didn't sustain — entry signal too soft")
        except (ValueError, TypeError):
            pass

    if exit_liq != "?" and entry_liq != "?":
        try:
            liq_drop_pct = (float(entry_liq) - float(exit_liq)) / float(entry_liq) * 100 if float(entry_liq) > 0 else 0
            if liq_drop_pct > 30:
                diagnosis_parts.append(f"liquidity dropped {liq_drop_pct:.0f}% — rug pull risk materializing")
        except (ValueError, TypeError):
            pass

    if holding_seconds is not None:
        hours = holding_seconds / 3600
        if hours > 12 and abs(pnl_pct) < 10:
            diagnosis_parts.append(f"held {hours:.1f}h with no clear direction — should have exited earlier")

    return {
        "diagnosis": ". ".join(diagnosis_parts),
        "entry_vs_exit": {
            "chg24_entry": entry_chg,
            "chg24_exit": exit_chg,
            "liq_entry": entry_liq,
            "liq_exit": exit_liq,
            "vol24_entry": entry_vol,
            "vol24_exit": exit_vol,
        },
        "fraction_sold": fraction,
    }


# =====================================================================
# Main loop
# =====================================================================

def compute_trade_stats(trades):
    """Aggregate stats across all closed trades."""
    if not trades:
        return {"total": 0, "wins": 0, "losses": 0, "win_rate_pct": 0,
                "total_pnl_sol": 0, "avg_pnl_pct": 0, "best_pnl_pct": 0, "worst_pnl_pct": 0}
    wins = [t for t in trades if t.get("pnl_sol", 0) > 0]
    losses = [t for t in trades if t.get("pnl_sol", 0) <= 0]
    pnls_pct = [t.get("pnl_pct", 0) for t in trades]
    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(trades), 1),
        "total_pnl_sol": round(sum(t.get("pnl_sol", 0) for t in trades), 6),
        "avg_pnl_pct": round(sum(pnls_pct) / len(pnls_pct), 2),
        "best_pnl_pct": round(max(pnls_pct), 2),
        "worst_pnl_pct": round(min(pnls_pct), 2),
    }


def git_commit_and_push():
    import subprocess
    cwd = WORK_DIR
    try:
        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True
        )
        if not result.stdout.strip():
            log("No changes to commit")
            return False
        subprocess.run(
            ["git", "commit", "-m", f"Bot update @ {now_utc().strftime('%H:%M')} UTC"],
            cwd=cwd, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"], cwd=cwd, check=True, capture_output=True, timeout=60
        )
        log("Pushed to oracle_Vault")
        return True
    except subprocess.CalledProcessError as e:
        log(f"ERROR git: {e}")
        return False


def main():
    log("=== Memecoin bot tick ===")
    state = load_state()
    now = now_utc()

    # 1. Fetch prices
    try:
        sol_price = fetch_sol_price_usd()
        if sol_price is None:
            log("ERROR: couldn't fetch SOL price")
            sys.exit(1)
        log(f"SOL price: ${sol_price:.4f}")
    except Exception as e:
        log(f"ERROR fetching SOL price: {e}")
        sys.exit(1)

    # 2. Fetch watchlist
    top_runners = fetch_pumpfun_top_runners(limit=30)
    log(f"pump.fun top-runners: {len(top_runners)} tokens")

    mints = [t["mint"] for t in top_runners if t.get("mint")]
    dex_data = fetch_dexscreener_for_mints(mints)
    log(f"DexScreener: {len(dex_data)} pairs")

    watchlist_state = build_watchlist_state(sol_price, top_runners, dex_data)
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps(watchlist_state, indent=2, ensure_ascii=False))

    state["last_sol_price_usd"] = sol_price

    # 3. Evaluate exits for open positions
    exits = []
    for mint, pos in list(state.get("positions", {}).items()):
        token = next((t for t in watchlist_state["tokens"] if t["mint"] == mint), None)
        if token is None:
            continue
        current_price = _to_float(token.get("price_usd"))
        current_change = _to_float(token.get("price_change_h24"))
        if current_price <= 0:
            continue

        # Compute holding time
        entry_time = parse_iso(pos.get("entry_time"))
        holding_seconds = (now - entry_time).total_seconds() if entry_time else None

        should_exit, reason, pnl_pct, action, fraction = evaluate_exit(
            pos, current_price, current_change, now
        )
        if should_exit:
            exit_signals = {
                "price_change_h24": current_change,
                "liquidity_usd": _to_float(token.get("liquidity_usd")),
                "volume_h24": _to_float(token.get("volume_h24")),
            }
            ok, trade = execute_sell(
                state, mint, current_price, reason, now,
                fraction=fraction, exit_signals=exit_signals,
                holding_seconds=holding_seconds,
            )
            if ok:
                exits.append((mint, trade))
                pm = trade.get("post_mortem", {})
                diagnosis = pm.get("diagnosis", "") if pm else ""
                action_label = "PARTIAL" if trade.get("partial") else "FULL"
                append_decision({
                    "action": "sell",
                    "details": f"[{action_label}] Closed ${trade['symbol']} ({mint[:8]}…) at ${current_price:.6g} | "
                               f"P&L: {trade['pnl_pct']:+.1f}% | {reason}",
                    "reason": diagnosis or reason,
                    "data": {"trade": trade, "post_mortem": pm},
                })

    if exits:
        for mint, trade in exits:
            log(f"SELL ${trade['symbol']}: {trade['pnl_pct']:+.1f}% — {trade['exit_reason']}")

    # 4. Find entry candidate (only if we have slots)
    entry = None
    candidate, entry_info = find_entry_candidate(state, watchlist_state, now)
    if candidate:
        token = entry_info["token"]
        price_usd = _to_float(token.get("price_usd"))
        if price_usd > 0:
            ok, position = execute_buy(state, candidate, token, price_usd, now)
            if ok:
                # Save the full score components for post-mortem later
                position["entry_score_components"] = entry_info.get("components", {})
                entry = (candidate, position, entry_info)
                breakdown = entry_info.get("components", {}).get("score_breakdown", {})
                append_decision({
                    "action": "buy",
                    "details": f"Bought ${position['symbol']} ({candidate[:8]}…) at ${price_usd:.6g}, "
                               f"spent {POSITION_SIZE_SOL} SOL (${position['entry_usd_value']:.2f})",
                    "reason": f"Score {entry_info['score']:.1f}: 24h={breakdown.get('base_24h', '?')}%, "
                              f"recency={breakdown.get('recency_bonus', 0)}, "
                              f"turnover={breakdown.get('turnover_bonus', 0)}, "
                              f"short_mom={breakdown.get('short_momentum', 0)}",
                    "data": {"position": position, "score_breakdown": breakdown},
                })
                log(f"BUY ${position['symbol']}: ${position['amount']:.4f} tokens @ ${price_usd:.6g} "
                    f"(score {entry_info['score']:.1f})")

    if entry is None and not exits:
        # No trades this tick — log observation
        held = len(state.get("positions", {}))
        free_slots = MAX_POSITIONS - held
        watchlist_count = len(watchlist_state.get("tokens", []))
        append_decision({
            "action": "observe",
            "details": f"No trades this tick. {held}/{MAX_POSITIONS} positions, "
                       f"{state.get('balance_sol', 0):.3f} SOL free, "
                       f"{watchlist_count} tokens watched",
            "reason": entry_info if isinstance(entry_info, str) else "candidate not found",
        })

    # 5. Portfolio + stats
    portfolio = compute_portfolio_value(state, sol_price, dex_data)
    stats = compute_trade_stats(state.get("trades", []))
    log(f"Portfolio: {portfolio['total_value_usd']} USD ({portfolio['sol_balance_value_usd']} SOL + "
        f"${portfolio['positions_value_usd']} positions). Trades: {stats}")

    # 6. Update state
    state["last_updated"] = iso_now()
    state["portfolio_value_usd"] = portfolio["total_value_usd"]
    state["balance_usd_estimate"] = portfolio["sol_balance_value_usd"]
    state["trade_stats"] = stats
    state["recent_decisions"] = load_recent_decisions(max_n=20)

    if state.get("starting_balance_usd") is None:
        state["starting_balance_usd"] = portfolio["total_value_usd"]

    save_state(state)
    save_trades_log(state)
    log(f"State saved. {len(state.get('positions', {}))} positions open, "
        f"{len(state.get('trades', []))} trades closed total.")

    # 7. Push
    git_commit_and_push()
    log("=== Done ===")


if __name__ == "__main__":
    main()