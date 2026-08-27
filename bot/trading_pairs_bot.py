#!/usr/bin/env python3
"""
Trading Pairs Bot — multi-pair, multi-strategy paper trading.

Runs every 60s. For each pair, evaluates 4 strategies (SUPER, ROC, BB, DIR).
Opens positions when signals fire, closes via TP/SL/time-stop.

Paper only. Uses Binance public API for live prices.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
WORK_DIR = SCRIPT_DIR.parent
WIKI_DIR = WORK_DIR / "wiki"
STATE_PATH = WIKI_DIR / "trading-pairs" / "state.json"
TRADES_PATH = WIKI_DIR / "trading-pairs" / "trades.json"
DECISIONS_PATH = WIKI_DIR / "trading-pairs" / "decisions.md"

# === Strategy parameters ===
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ARBUSDT"]
STRATEGIES = ["SUPER", "ROC", "BB", "DIR"]

POSITION_SIZE_USD = 100.0       # paper USD per position
MAX_POSITIONS_PER_PAIR = 3
MAX_TOTAL_POSITIONS = 15        # 6 pairs * 3 = 18 max possible, cap at 15
MAX_TOTAL_EXPOSURE_USD = 1500.0
TICK_SECONDS = 60

# Per-strategy TP / SL / time-stop
STRATEGY_PARAMS = {
    "SUPER": {"tp_pct": 1.5, "sl_pct": 1.0, "max_hold_h": 4.0},
    "ROC":   {"tp_pct": 3.0, "sl_pct": 2.0, "max_hold_h": 3.0},
    "BB":    {"tp_pct": 5.0, "sl_pct": 3.0, "max_hold_h": 4.0},
    "DIR":   {"tp_pct": 8.0, "sl_pct": 2.0, "max_hold_h": 168.0},  # weekly hold
}

INITIAL_BANKROLL_USD = 1000.0  # paper USD
TIMEOUT = 10

USER_AGENT = "oracle-vault-trading-pairs/1.0"


# === Utilities ===
def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())


def now_utc():
    return datetime.now(timezone.utc)


def iso_now():
    return now_utc().isoformat()


# === Data ===
def fetch_tickers(pairs):
    """Fetch current prices for all pairs."""
    syms = "%5B" + "%2C".join(f"%22{p}%22" for p in pairs) + "%5D"
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbols={syms}"
    data = http_get_json(url)
    return {x["symbol"]: x for x in data}


def fetch_klines(symbol, interval="15m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    return http_get_json(url)


# === Indicators ===
def ema(values, period):
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def sma(values, period):
    if len(values) < period:
        return [None] * len(values)
    out = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        out.append(sum(values[i - period + 1: i + 1]) / period)
    return out


def stdev(values, period):
    out = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        chunk = values[i - period + 1: i + 1]
        avg = sum(chunk) / period
        out.append((sum((x - avg) ** 2 for x in chunk) / period) ** 0.5)
    return out


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(1, period + 1):
        ch = closes[i] - closes[i - 1]
        if ch > 0:
            gains += ch
        else:
            losses -= ch
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def roc(closes, period=15):
    if len(closes) < period + 1:
        return 0
    return (closes[-1] / closes[-period - 1] - 1) * 100


def bollinger(closes, period=20, num_std=2):
    if len(closes) < period:
        return None
    chunk = closes[-period:]
    mid = sum(chunk) / period
    var = sum((x - mid) ** 2 for x in chunk) / period
    sd = var ** 0.5
    return {"upper": mid + num_std * sd, "middle": mid, "lower": mid - num_std * sd}


# === Strategies ===
def strategy_signal(strategy, closes):
    """Returns 'LONG' / 'SHORT' / 'FLAT' (DIR is always LONG or FLAT)."""
    if strategy == "SUPER":
        if len(closes) < 50:
            return "FLAT"
        e20 = ema(closes, 20)[-1]
        e50 = ema(closes, 50)[-1]
        return "LONG" if e20 > e50 else "FLAT"
    if strategy == "ROC":
        if len(closes) < 16:
            return "FLAT"
        r = roc(closes, 15)
        return "LONG" if r > 2.0 else "FLAT"
    if strategy == "BB":
        bb = bollinger(closes)
        if bb is None:
            return "FLAT"
        last = closes[-1]
        return "LONG" if last > bb["upper"] else "FLAT"
    if strategy == "DIR":
        # Always long for baseline (paper trading buy-and-hold)
        return "LONG"
    return "FLAT"


# === State ===
def load_state():
    if not STATE_PATH.exists():
        return _fresh_state()
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return _fresh_state()


def _fresh_state():
    return {
        "bankroll_usd": INITIAL_BANKROLL_USD,
        "positions": {},  # mint -> {pair, strategy, side, size_usd, entry_price, entry_time, ...}
        "trades": [],     # closed trades
        "last_tick": None,
        "bot_version": "1.0",
        "started": iso_now(),
    }


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def append_decision(state, action, details):
    """Append to decisions.md for human-readable audit."""
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DECISIONS_PATH.exists():
        DECISIONS_PATH.write_text(
            "# Trading Pairs Decisions Log\n\n> v1 — multi-pair, multi-strategy paper trading.\n\n"
        )
    ts = now_utc().strftime("%Y-%m-%d %H:%M UTC")
    with open(DECISIONS_PATH, "a") as f:
        f.write(f"## [{ts}] {action} | {details}\n\n")


# === Position management ===
def position_key(pair, strategy):
    return f"{pair}:{strategy}"


def compute_position_pnl(pos, current_price):
    """Returns (pnl_usd, pnl_pct, current_value_usd) for an open position."""
    entry = pos["entry_price"]
    if pos["side"] == "LONG":
        delta_pct = (current_price - entry) / entry * 100
    else:  # SHORT
        delta_pct = (entry - current_price) / entry * 100
    pnl_usd = pos["size_usd"] * delta_pct / 100
    current_value = pos["size_usd"] + pnl_usd
    return pnl_usd, delta_pct, current_value


def should_exit(pos, current_price, now):
    """Returns (should_exit: bool, reason: str) for an open position."""
    if pos["side"] != "LONG":  # we only go long in v1
        return False, ""
    params = STRATEGY_PARAMS.get(pos["strategy"], STRATEGY_PARAMS["SUPER"])
    entry = pos["entry_price"]
    pnl_pct = (current_price - entry) / entry * 100

    # TP
    if pnl_pct >= params["tp_pct"]:
        return True, f"TP +{pnl_pct:.1f}%"

    # SL
    if pnl_pct <= -params["sl_pct"]:
        return True, f"SL {pnl_pct:.1f}%"

    # Time-stop
    held_h = (now - datetime.fromisoformat(pos["entry_time"])).total_seconds() / 3600
    if held_h >= params["max_hold_h"]:
        return True, f"time-stop {held_h:.1f}h"

    return False, ""


def open_position(state, pair, strategy, signal, price, now):
    """Open a position if signal != FLAT. Returns (success: bool, msg: str)."""
    key = position_key(pair, strategy)
    if key in state["positions"]:
        return False, f"already have {key}"

    # Check position caps
    if len(state["positions"]) >= MAX_TOTAL_POSITIONS:
        return False, "max total positions"
    per_pair = sum(1 for p in state["positions"].values() if p["pair"] == pair)
    if per_pair >= MAX_POSITIONS_PER_PAIR:
        return False, "max per-pair positions"
    # Check exposure
    exposure = sum(p["size_usd"] for p in state["positions"].values())
    if exposure + POSITION_SIZE_USD > MAX_TOTAL_EXPOSURE_USD:
        return False, "max exposure"

    if signal == "FLAT":
        return False, "FLAT signal"

    size_usd = POSITION_SIZE_USD
    # Approximate token amount (for tracking; crypto is fractional)
    token_amount = size_usd / price if price > 0 else 0

    state["positions"][key] = {
        "pair": pair,
        "strategy": strategy,
        "side": signal,
        "size_usd": size_usd,
        "entry_price": price,
        "entry_time": iso_now(),
        "token_amount": token_amount,
    }
    return True, f"opened {signal} {pair} @ ${price:.4f}"


def close_position(state, key, price, reason, now):
    """Close a position, record the trade."""
    pos = state["positions"].get(key)
    if not pos:
        return None
    pnl_usd, pnl_pct, exit_value = compute_position_pnl(pos, price)
    trade = {
        "pair": pos["pair"],
        "strategy": pos["strategy"],
        "side": pos["side"],
        "size_usd": pos["size_usd"],
        "entry_price": pos["entry_price"],
        "entry_time": pos["entry_time"],
        "exit_price": price,
        "exit_time": iso_now(),
        "exit_reason": reason,
        "pnl_usd": round(pnl_usd, 4),
        "pnl_pct": round(pnl_pct, 2),
        "held_h": round((now - datetime.fromisoformat(pos["entry_time"])).total_seconds() / 3600, 2),
    }
    state["trades"].append(trade)
    # Update bankroll
    state["bankroll_usd"] = round(state.get("bankroll_usd", INITIAL_BANKROLL_USD) + pnl_usd, 4)
    del state["positions"][key]
    return trade


# === Main tick ===
def main():
    log("=== Trading Pairs Bot tick ===")
    state = load_state()
    now = now_utc()
    log(f"Bankroll: ${state.get('bankroll_usd', 0):.2f}  Positions: {len(state.get('positions', {}))}")

    # 1. Fetch tickers for all pairs
    try:
        tickers = fetch_tickers(PAIRS)
    except Exception as e:
        log(f"ERROR fetching tickers: {e}")
        return

    # 2. Check exits on open positions
    for key in list(state["positions"].keys()):
        pos = state["positions"][key]
        ticker = tickers.get(pos["pair"])
        if not ticker:
            continue
        price = float(ticker["lastPrice"])
        do_exit, reason = should_exit(pos, price, now)
        if do_exit:
            trade = close_position(state, key, price, reason, now)
            if trade:
                log(f"CLOSE {key}: {reason} → P&L ${trade['pnl_usd']:+.2f} ({trade['pnl_pct']:+.1f}%)")
                append_decision(state, "close", f"{trade['pair']} {trade['strategy']} {reason} P&L={trade['pnl_pct']:+.1f}%")

    # 3. Evaluate entry signals on (pair, strategy) combos without open position
    opens = 0
    for pair in PAIRS:
        ticker = tickers.get(pair)
        if not ticker:
            continue
        price = float(ticker["lastPrice"])
        # Fetch klines for indicators (1 call per pair per tick)
        try:
            klines = fetch_klines(pair, "15m", 100)
        except Exception as e:
            log(f"WARN: klines fetch {pair} failed: {e}")
            continue
        closes = [float(k[4]) for k in klines]
        for strategy in STRATEGIES:
            key = position_key(pair, strategy)
            if key in state["positions"]:
                continue  # already have one
            signal = strategy_signal(strategy, closes)
            if signal != "FLAT":
                ok, msg = open_position(state, pair, strategy, signal, price, now)
                if ok:
                    opens += 1
                    log(f"OPEN {msg}")
                    append_decision(state, "open", f"{pair} {strategy} {signal} @ ${price:.4f}")
                # else: silent skip (likely cap reached)

    # 4. Compute portfolio value
    total_value = state.get("bankroll_usd", INITIAL_BANKROLL_USD)
    for key, pos in state["positions"].items():
        ticker = tickers.get(pos["pair"])
        if ticker:
            _, _, current_value = compute_position_pnl(pos, float(ticker["lastPrice"]))
            total_value += current_value
    total_pnl = total_value - INITIAL_BANKROLL_USD
    log(f"Total value: ${total_value:.2f}  P&L: ${total_pnl:+.2f} ({total_pnl/INITIAL_BANKROLL_USD*100:+.1f}%)")

    # 5. Build dashboard data
    state["last_tick"] = iso_now()
    state["total_value_usd"] = round(total_value, 2)
    state["total_pnl_usd"] = round(total_pnl, 2)
    state["total_pnl_pct"] = round(total_pnl / INITIAL_BANKROLL_USD * 100, 2)
    state["prices"] = {
        p: {
            "price": float(tickers[p]["lastPrice"]),
            "change_24h_pct": float(tickers[p]["priceChangePercent"]),
            "high_24h": float(tickers[p]["highPrice"]),
            "low_24h": float(tickers[p]["lowPrice"]),
            "volume_24h": float(tickers[p]["volume"]),
        }
        for p in PAIRS if p in tickers
    }
    save_state(state)
    log(f"State saved. Opens this tick: {opens}")

    # 6. Git push
    cwd = WORK_DIR
    try:
        import subprocess
        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True, capture_output=True)
        result = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            return
        subprocess.run(
            ["git", "commit", "-m", f"Pairs bot tick @ {now.strftime('%H:%M')} UTC"],
            cwd=cwd, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=cwd, check=True, capture_output=True, timeout=60
        )
        log("Pushed")
    except Exception as e:
        log(f"git error: {e}")


if __name__ == "__main__":
    main()
