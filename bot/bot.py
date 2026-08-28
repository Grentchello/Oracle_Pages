#!/usr/bin/env python3
"""
Memecoin Trading Bot — v4 (Attention-First LLM)

Memecoins are attention markets, not logic. This bot:
- Scans freshly-launched tokens (not just top-runners)
- Shows LLM narrative context (name, description, X link)
- Drops aggressive liquidity/volume gates
- Asks the LLM to be opportunistic, not defensive
- Lets the LLM trade on attention

Run: python3 bot.py
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import threading
from datetime import datetime, timezone
from pathlib import Path

# === Paths ===
SCRIPT_DIR = Path(__file__).parent.resolve()
WORK_DIR = SCRIPT_DIR.parent
WIKI_DIR = WORK_DIR / "wiki"
STATE_PATH = WIKI_DIR / "trading" / "state.json"
DECISIONS_PATH = WIKI_DIR / "trading" / "decisions.md"
WATCHLIST_PATH = WIKI_DIR / "trading" / "watchlist.json"
TRADES_PATH = WIKI_DIR / "trading" / "trades.json"
DECISION_LOG_PATH = WIKI_DIR / "trading" / "decision_log.json"
LAST_SEEN_PATH = WIKI_DIR / "trading" / "last_seen_mints.json"
SPARKLINE_PATH = WIKI_DIR / "trading" / "sparklines.json"
HAS_SPARKLINES = SPARKLINE_PATH.exists()

# === APIs ===
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
PUMPFUN_TOP_RUNNERS = "https://frontend-api-v3.pump.fun/coins/top-runners"
PUMPFUN_RECOMMENDED = "https://frontend-api-v3.pump.fun/coins/recommended"
# Newest launches: sort by created_timestamp DESC. Returns truly fresh tokens.
PUMPFUN_NEW_LAUNCHES = "https://frontend-api-v3.pump.fun/coins?limit=30&offset=0&sort=created_timestamp&order=DESC&includeNsfw=false"
SOL_MINT = "So11111111111111111111111111111111111111112"

# === Strategy parameters (safeguards — LLM can't override) ===
POSITION_SIZE_SOL = 0.05         # $5 per position (halved from 0.1 in v7)
MAX_POSITIONS = 5
MAX_HOLD_HOURS = 72
HARD_STOP_LOSS = 0.30        # -30% hard cap (tightened from -50% in v7)
DAILY_MAX_LOSS_SOL = 0.20    # daily loss cap -0.20 SOL (was -0.4; tighter in v7)
RESERVE_SOL = 0.05

# LLM throttling
LLM_BRIEF_INTERVAL_MIN = 5  # when idle, LLM ticks every 5 min
ALWAYS_LLM_TICK = True

# === LLM config ===
HERMES_CLI = "/opt/hermes/.venv/bin/hermes"
LLM_TIMEOUT_SECONDS = 90

# === Network ===
TIMEOUT = 15
USER_AGENT = "oracle-vault-memecoin-bot/4.0"


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
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# =====================================================================
# Data fetchers — expanded to include fresh launches
# =====================================================================

def fetch_pumpfun_freshest(limit=30):
    """Truly new launches: sort by created_timestamp DESC. Filters out old tokens."""
    try:
        data = http_get_json(PUMPFUN_NEW_LAUNCHES + f"&limit={limit}")
        items = data if isinstance(data, list) else data.get("coins", [])
        out = []
        now_ms = now_utc().timestamp() * 1000
        for coin in items[:limit]:
            mint = coin.get("mint")
            if not mint:
                continue
            age_min = None
            if coin.get("created_timestamp"):
                age_min = (now_ms - coin["created_timestamp"]) / 60000
                # Skip anything older than 6 hours — alpha is gone
                if age_min > 360:
                    continue
            out.append({
                "mint": mint,
                "symbol": coin.get("symbol", "?"),
                "name": coin.get("name", "?"),
                "description": (coin.get("description") or "")[:300],
                "twitter": coin.get("twitter") or "",
                "telegram": coin.get("telegram") or "",
                "website": coin.get("website") or "",
                "image_uri": coin.get("image_uri") or "",
                "created_ts": coin.get("created_timestamp"),
                "age_min": round(age_min, 1) if age_min is not None else None,
                "last_trade_ts": coin.get("last_trade_timestamp"),
                "market_cap_usd": _to_float(coin.get("usd_market_cap") or coin.get("market_cap_usd")),
                "ath_market_cap_usd": _to_float(coin.get("ath_market_cap")),
                "real_sol_reserves": _to_float(coin.get("real_sol_reserves")) / 1e9,
                "virtual_sol_reserves": _to_float(coin.get("virtual_sol_reserves")) / 1e9,
                "real_token_reserves": _to_float(coin.get("real_token_reserves")) / 1e6,
                "virtual_token_reserves": _to_float(coin.get("virtual_token_reserves")) / 1e6,
                # bonding curve progress: 0% = just launched, 100% = graduated
                "bonding_progress": (
                    _to_float(coin.get("real_sol_reserves")) /
                    (_to_float(coin.get("virtual_sol_reserves")) + _to_float(coin.get("real_sol_reserves"))) * 100
                    if (_to_float(coin.get("virtual_sol_reserves")) + _to_float(coin.get("real_sol_reserves"))) > 0
                    else 0
                ),
                "complete": coin.get("complete", False),
                "king_of_hill": bool(coin.get("king_of_the_hill_timestamp")),
                "boost_mode": coin.get("boost_mode"),
                "source_endpoint": "new-launches",
            })
        return out
    except Exception as e:
        log(f"WARN: new launches fetch failed: {e}")
        return []


def fetch_pumpfun_coin(mint):
    """Single-coin data from pump.fun. Used for held positions whose DexScreener pair is missing."""
    try:
        return http_get_json(f"https://frontend-api-v3.pump.fun/coins/{mint}")
    except Exception as e:
        log(f"WARN: pump.fun coin fetch {mint[:8]} failed: {e}")
        return None


def fetch_pumpfun_top_runners(limit=20):
    """Pump.fun's own algorithm-recommended tokens."""
    try:
        data = http_get_json(PUMPFUN_TOP_RUNNERS)
        items = data if isinstance(data, list) else data.get("coins", [])
        out = []
        for coin in items[:limit]:
            mint = coin.get("mint")
            if not mint:
                continue
            out.append({
                "mint": mint,
                "symbol": coin.get("symbol", "?"),
                "name": coin.get("name", "?"),
                "description": (coin.get("description") or "")[:300],
                "twitter": coin.get("twitter") or "",
                "market_cap_usd": _to_float(coin.get("usd_market_cap") or coin.get("market_cap_usd")),
                "ath_market_cap_usd": _to_float(coin.get("ath_market_cap")),
                "last_trade_ts": coin.get("last_trade_timestamp"),
                "complete": coin.get("complete", False),
                "source_endpoint": "top-runners",
            })
        return out
    except Exception as e:
        log(f"WARN: top-runners fetch failed: {e}")
        return []


def fetch_dexscreener_for_mints(mints):
    """Fetch DexScreener pair data. Returns mint -> pair."""
    out = {}
    if not mints:
        return out
    try:
        data = http_get_json(f"{DEXSCREENER_BASE}/tokens/{','.join(mints[:30])}")
        for pair in data.get("pairs") or []:
            mint = pair.get("baseToken", {}).get("address")
            if not mint:
                continue
            new_liq = _to_float((pair.get("liquidity") or {}).get("usd"))
            existing = out.get(mint)
            existing_liq = _to_float((existing.get("liquidity") or {}).get("usd")) if existing else 0
            if existing is None or new_liq > existing_liq:
                out[mint] = pair
    except Exception as e:
        log(f"WARN: DexScreener fetch failed: {e}")
    return out


# =====================================================================
# State
# =====================================================================

def load_state():
    if not STATE_PATH.exists():
        return _fresh_state()
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return _fresh_state()


def _fresh_state():
    return {
        "balance_sol": 2.0,
        "positions": {},
        "trades": [],
        "bot_version": "4.0-attention",
    }


def save_state(state):
    import sys
    print(f"[save_state] Writing {len(state.get('positions', {}))} positions, {len(state.get('trades', []))} trades to {STATE_PATH}", file=sys.stderr, flush=True)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    print(f"[save_state] Done, mtime now", file=sys.stderr, flush=True)


def load_last_seen_mints():
    if LAST_SEEN_PATH.exists():
        try:
            return set(json.loads(LAST_SEEN_PATH.read_text()))
        except Exception:
            return set()
    return set()


def save_last_seen_mints(mints):
    LAST_SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_SEEN_PATH.write_text(json.dumps(sorted(mints), indent=2))


def append_decision(decision):
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DECISIONS_PATH.exists():
        DECISIONS_PATH.write_text(
            "# Bot Decisions Log\n\n"
            "> v4 — Attention-first LLM trading. Each entry shows bot action + reasoning.\n\n"
        )
    ts = now_utc().strftime("%Y-%m-%d %H:%M UTC")
    line = f"## [{ts}] {decision['action']} | {decision.get('details', '')}\n"
    if decision.get("reason"):
        line += f"- **Reasoning:** {decision['reason']}\n"
    if decision.get("data"):
        line += f"- Data: `{json.dumps(decision['data'], ensure_ascii=False)[:500]}`\n"
    line += "\n"
    with open(DECISIONS_PATH, "a") as f:
        f.write(line)


def log_full_decision(prompt, response, action, target):
    log_data = []
    if DECISION_LOG_PATH.exists():
        try:
            log_data = json.loads(DECISION_LOG_PATH.read_text())
        except Exception:
            log_data = []
    log_data.append({
        "time": iso_now(),
        "target": target,
        "action": action,
        "prompt": prompt[:2000],
        "response": response[:8000],
    })
    log_data = log_data[-100:]
    DECISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DECISION_LOG_PATH.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))


def load_recent_decisions(max_n=20):
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
            current = {"time": m.group(1), "action": m.group(2), "details": m.group(3), "reason": ""}
        elif current:
            rm = re.match(r"^- \*\*Reasoning:\*\* (.*)$", line)
            if rm:
                current["reason"] = rm.group(1)
    if current:
        decisions.append(current)
    return decisions[-max_n:]


def compute_portfolio_value(state, sol_price, dex_data):
    positions_value_usd = 0.0
    for mint, pos in state.get("positions", {}).items():
        pair = dex_data.get(mint)
        if pair and _to_float(pair.get("priceUsd")) > 0:
            positions_value_usd += pos["amount"] * _to_float(pair["priceUsd"])
        elif pos.get("entry_price_usd"):
            positions_value_usd += pos["amount"] * pos["entry_price_usd"]
    sol_value = state.get("balance_sol", 0) * sol_price
    return {
        "sol_balance_value_usd": round(sol_value, 2),
        "positions_value_usd": round(positions_value_usd, 2),
        "total_value_usd": round(sol_value + positions_value_usd, 2),
    }


def compute_today_realized_pnl(state):
    today = now_utc().date()
    total = 0.0
    for t in state.get("trades", []):
        exit_dt = parse_iso(t.get("exit_time"))
        if exit_dt and exit_dt.date() == today:
            total += _to_float(t.get("pnl_sol", 0))
    return round(total, 6)


def compute_trade_stats(state):
    """Aggregate stats across all closed trades."""
    trades = state.get("trades", [])
    if not trades:
        return {"total": 0, "wins": 0, "losses": 0, "win_rate_pct": 0,
                "total_pnl_sol": 0, "avg_pnl_pct": 0, "best_pnl_pct": 0,
                "worst_pnl_pct": 0, "today_trades": 0, "today_realized_sol": 0,
                "today_target_pct": -100, "daily_target_pct": 20.0,
                "learning": {"win_count": 0, "loss_count": 0,
                             "note": "no trades yet"}}
    wins = [t for t in trades if _to_float(t.get("pnl_sol", 0)) > 0]
    losses = [t for t in trades if _to_float(t.get("pnl_sol", 0)) <= 0]
    pnls = [_to_float(t.get("pnl_pct", 0)) for t in trades]
    pnls_sol = [_to_float(t.get("pnl_sol", 0)) for t in trades]
    today = now_utc().date()
    today_pnls = [_to_float(t.get("pnl_sol", 0)) for t in trades
                 if parse_iso(t.get("exit_time"))
                 and parse_iso(t.get("exit_time")).date() == today]
    today_realized = sum(today_pnls)
    avg = round(sum(pnls) / len(pnls), 2) if pnls else 0
    target_sol = 0.4  # 2 SOL * 20% target
    today_target_pct = round(today_realized / target_sol * 100, 1) if target_sol else 0
    return {
        "total": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1),
        "total_pnl_sol": round(sum(pnls_sol), 6),
        "avg_pnl_pct": avg,
        "best_pnl_pct": round(max(pnls), 2) if pnls else 0,
        "worst_pnl_pct": round(min(pnls), 2) if pnls else 0,
        "today_trades": len(today_pnls),
        "today_realized_sol": round(today_realized, 6),
        "today_target_pct": today_target_pct,
        "daily_target_pct": 20.0,
        "learning": {
            "win_count": len(wins),
            "loss_count": len(losses),
            "note": "need ≥3 wins and ≥3 losses for signal analysis" if len(wins) < 3 or len(losses) < 3 else "ready for analysis",
        },
    }


# =====================================================================
# LLM
# =====================================================================

def call_llm(prompt, max_seconds=LLM_TIMEOUT_SECONDS):
    try:
        result = subprocess.run(
            [HERMES_CLI, "chat", "-q", prompt, "-Q",
             "--max-turns", "1", "--run-budget", str(max_seconds),
             "--ignore-rules", "--safe-mode",
             "-t", "terminal"],
            capture_output=True, text=True, timeout=max_seconds + 30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"hermes chat failed (rc={result.returncode}): {result.stderr[:300]}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"LLM call timed out after {max_seconds}s")


def extract_json(text):
    # 1. Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # 2. Try code-fenced JSON (multi-line OK)
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 3. Try to find the FIRST { and match it with a brace-balanced close
    start = text.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except Exception:
                        break
    return None


# =====================================================================
# Build the prompt — ATTENTION FIRST
# =====================================================================

def build_decision_prompt(state, sol_price, watchlist_data, portfolio, today_pnl, new_mints, held_prices=None):
    """v4: LLM gets narrative context + new-launch alerts."""

    positions = state.get("positions", {})
    held_prices = held_prices or {}

    # === Held positions with context ===
    held = []
    for mint, pos in positions.items():
        entry_price = _to_float(pos.get("entry_price_usd"))
        held_hours = 0
        if pos.get("entry_time"):
            held_hours = (now_utc() - parse_iso(pos["entry_time"])).total_seconds() / 3600

        # Prefer held_prices (always fetched). Fall back to watchlist if held_prices missing.
        hprice = held_prices.get(mint) or {}
        cur_price = hprice.get("price_usd") or 0
        if cur_price <= 0:
            token = next((t for t in watchlist_data["tokens"] if t["mint"] == mint), None)
            if token:
                cur_price = _to_float(token.get("price_usd"))

        pnl_pct = ((cur_price / entry_price - 1) * 100) if cur_price > 0 and entry_price > 0 else None
        # Load price + market cap history (sparkline) for this mint if available
        price_history = None
        if HAS_SPARKLINES and SPARKLINE_PATH.exists():
            try:
                sl_data = json.loads(SPARKLINE_PATH.read_text())
                mint_data = sl_data.get(mint, {})
                if mint_data.get("ts"):
                    # Last 30 buckets (30 min) — compress to 10 data points for prompt
                    ts_list = mint_data["ts"][-30:]
                    px_list = mint_data.get("px", [])[-30:]
                    mc_list = mint_data.get("mc", [])[-30:]
                    if len(ts_list) >= 2:
                        # Compress to 10 evenly-spaced points
                        n = len(ts_list)
                        step = max(1, n // 10)
                        sampled_ts = ts_list[::step][:10]
                        sampled_px = px_list[::step][:10]
                        sampled_mc = mc_list[::step][:10] if mc_list else [0]*len(sampled_ts)
                        # Show as "T-Nmin: $price (MC: X SOL)"
                        now_ts = int(time.time())
                        history_str = ", ".join([
                            f"{int((now_ts-t)/60)}min: ${p:.10f} (MC:{m:.1f})"
                            for t, p, m in zip(sampled_ts, sampled_px, sampled_mc)
                        ])
                        price_history = history_str
            except Exception:
                pass
        held.append({
            "symbol": pos.get("symbol"),
            "mint": mint,
            "amount_tokens": pos.get("amount"),
            "entry_price_usd": entry_price,
            "current_price_usd": cur_price,
            "pnl_pct": round(pnl_pct, 1) if pnl_pct is not None else None,
            "held_hours": round(held_hours, 1),
            "change_24h": hprice.get("change_24h"),
            "change_1h": hprice.get("change_1h"),
            "liquidity_usd": hprice.get("liquidity_usd"),
            "volume_h24": hprice.get("volume_h24"),
            "pos_value_usd": round((pos.get("amount", 0) * cur_price), 2) if cur_price > 0 else 0,
            "pos_pct_of_liq": round(((pos.get("amount", 0) * cur_price) / hprice.get("liquidity_usd", 0) * 100), 1) if cur_price > 0 and hprice.get("liquidity_usd", 0) > 0 else None,
            "real_sol_reserves": hprice.get("real_sol_reserves"),
            "dex_id": hprice.get("dex_id"),
            "price_source": hprice.get("source", "missing"),
            # Stale flag: held >15 min AND pnl < +10%
            "stale": held_hours > 0.25 and pnl_pct is not None and pnl_pct < 10,
            "stale_warning": " ⚠ STALE" if (held_hours > 0.25 and pnl_pct is not None and pnl_pct < 10) else "",
            "price_history_30m": price_history,
        })

    # === All candidate tokens (no filters) ===
    # The LLM should see the full list and decide which to buy
    held_mints = set(positions.keys())
    candidates = []
    for token in watchlist_data.get("tokens", []):
        if token["mint"] in held_mints:
            continue
        # Mark if this is a fresh launch we haven't seen
        is_new = token["mint"] in new_mints
        candidates.append({
            **token,
            "is_new_launch": is_new,
        })
    # Sort: by bonding progress (graduating first) DESC, then newest, then largest mcap
    candidates.sort(key=lambda c: (
        -(c.get("bonding_progress", 0) or 0),  # graduating first
        -(c.get("created_ts", 0) or 0),  # newer first
    ))
    candidates = candidates[:15]

    new_launch_alert = ""
    if new_mints:
        new_tokens_info = [c for c in candidates if c.get("is_new_launch")][:5]
        if new_tokens_info:
            new_launch_alert = (
                f"\n# NEW LAUNCHES DETECTED (not seen last tick) — these are fresh attention:\n"
                + "\n".join([
                    f"  - ${t['symbol']} ({t['name']}) — mcap ${t.get('market_cap_usd', 0):,.0f}, age ~{round((now_utc().timestamp()*1000 - (t.get('created_ts') or 0))/60000, 1)}min"
                    + (f" — twitter: {t['twitter']}" if t.get('twitter') else "")
                    + (f" — desc: {t.get('description', '')[:100]}" if t.get('description') else "")
                    for t in new_tokens_info
                ])
                + "\n"
            )

    prompt = f"""You are a memecoin trading bot. Memecoins are ATTENTION MARKETS, not logic. Your job is to find tokens with viral attention and ride the wave.

# IMPORTANT CONTEXT
You are running on a FRESH 2 SOL paper balance. The slate is clean. Your job is to **discover** if attention-launched memecoins can be traded profitably — not to protect capital from past losses. Past losses came from rules that have been replaced. This is a NEW strategy with a NEW prompt. You cannot lose money you haven't risked yet.

This is a learning experiment. If you skip every tick, you learn nothing. The whole point is to take positions, observe outcomes, and refine. Sitting in cash forever teaches us nothing.

## SCALPING DISCIPLINE (READ THIS)

Most memecoin traders hold for seconds to minutes. The fastest money is in fresh launches that pump 50-300% in their first hour. Hold too long and you give back gains.

**Hard rules the bot enforces (you can't override):**
- -30% hard stop loss (auto; tightened from -50% in v7)
- +30% take-profit at 25% (auto), +100% at 50%, +200% at 75%, +500% at 100%
- >30 min held AND not up >20% = stale exit (auto)
- >15 min held AND not up >10% = marked ⚠ STALE in your prompt
- Max hold 72h
- Daily loss cap -0.20 SOL (tightened from -0.4 in v7)
- Min liquidity 5x position size
- Position size 0.05 SOL ($5 per position, halved from 0.1 in v7)
- Viability gate (v8.1, from CoinCLIP paper arXiv:2412.07591): description ≥50 chars AND (twitter OR liquidity ≥$3k). Tokens failing this filter are SKIPPED automatically — LLM cannot override.
- Fragility gate (v8.2, from ME2F paper arXiv:2512.00377): blocklist of political/celebrity keywords (trump, musk, biden, melania, libra, kanye, putin, etc.). ME2F found these are most fragile (whale concentration 90%+, sentiment amplification 20%+). LLM cannot override.

**Your job:**
1. **SOLD POSITIONS — when do you have discretion?** Only on positions NOT yet at TP thresholds. If bot already auto-took-profit, no action needed.
2. **PROFIT-TAKING — be aggressive.** If up >20% and you have ANY doubt about whether it'll keep pumping, sell_all or sell_half. Don't hope. Lock the gain.
3. **LOSERS — exit fast.** If down >20% and no clear bounce signal, sell_all. -20% losses become -50% quickly. Don't hope.
4. **STALE POSITIONS — flat for >30 min?** Strongly consider exit. Stale capital = locked slot.
5. **ENTRIES — be picky.** Skip if no clear narrative, weak liquidity, or you've already entered that mint.

**Default bias: take the trade.** If you're up >15% and unsure, take profit. If you're at break-even and nothing's moving, exit. Capital rotation beats bag-holding.

# Current state
- SOL free: {state.get('balance_sol', 0):.4f} SOL (${state.get('balance_sol', 0) * sol_price:.2f})
- Open positions: {len(held)}/{MAX_POSITIONS}
- Total portfolio: ${portfolio['total_value_usd']:.2f}
- Today's realized P&L: {today_pnl:+.4f} SOL (fresh slate, doesn't reflect past losses)
- Daily target: +20% (0.4 SOL). Hard daily loss cap: -{DAILY_MAX_LOSS_SOL} SOL (no new entries if exceeded)
- All-time this experiment: 0 trades
- **Hard cap on any single position loss: -{int(HARD_STOP_LOSS*100)}%. LLM cannot override this.**

No prior trades — fresh slate.
"""
    prompt += new_launch_alert
    if held:
        prompt += "\n# Held positions (decide: hold / sell_all / sell_half)\n"
        for h in held:
            pnl_str = f"{h['pnl_pct']:+.1f}%" if h['pnl_pct'] is not None else "no current price"
            chg24 = h.get('change_24h')
            chg24_str = f", 24h={chg24:+.1f}%" if chg24 is not None else ""
            chg1 = h.get('change_1h')
            chg1_str = f", 1h={chg1:+.1f}%" if chg1 is not None else ""
            src = f" [{h.get('price_source', '?')}]" if h.get('price_source') and h.get('price_source') != "missing" else ""
            cur_str = f"${h['current_price_usd']:.10f}" if h.get('current_price_usd', 0) > 0 else "no current price"
            full_mint = h.get('mint', '')
            liq_str = ""
            if h.get('liquidity_usd', 0) > 0:
                pct = h.get('pos_pct_of_liq')
                pct_str = f"{pct:.0f}%" if pct is not None else "?"
                warn = " ⚠ HUGE" if pct and pct > 100 else (" ⚠" if pct and pct > 30 else "")
                liq_str = f", pool=${h['liquidity_usd']:.0f}, our share={pct_str}{warn}"
            sparkline_str = ""
            ph = h.get('price_history_30m')
            if ph:
                # Compress the price history into a tiny ASCII sparkline
                prices = []
                for tok in ph.split(", "):
                    if "$" in tok:
                        try:
                            prices.append(float(tok.split("$")[1]))
                        except (ValueError, IndexError):
                            pass
                if len(prices) >= 2:
                    spark_chars = "▁▂▃▄▅▆▇█"
                    min_p, max_p = min(prices), max(prices)
                    rng = max_p - min_p if max_p > min_p else 1
                    sparkline_str = " " + "".join([
                        spark_chars[min(7, int((p - min_p) / rng * 7))]
                        for p in prices
                    ])
            prompt += f"  - ${h['symbol']} entry ${h['entry_price_usd']:.10f} now {cur_str} = {pnl_str}, held {h['held_hours']:.1f}h{chg24_str}{chg1_str}{src}{liq_str}{h.get('stale_warning', '')}{sparkline_str}\n"
            prompt += f"      mint={full_mint}\n"
            if ph:
                prompt += f"      history_30m: {ph}\n"
        prompt += "\n"

    if candidates:
        prompt += "# Token candidates — RECENT LAUNCHES (last 6 hours). SOL price: $" + f"{sol_price:.2f}\n"
        for c in candidates:
            flag = "🆕 " if c.get("is_new_launch") else "  "
            mcap = c.get('market_cap_usd', 0)
            desc = c.get('description', '')[:120].replace('\n', ' ').replace('"', "'")
            age = c.get('age_min', '?')
            bonding = c.get('bonding_progress', 0)
            tweet = c.get('twitter', '')[:50]
            full_mint = c.get('mint', '')
            prompt += f"  {flag}${c['symbol']:10} ({c['name'][:24]:24}) age={str(age)+'min':>8} mcap=${mcap:>9,.0f} bond={bonding:.0f}% complete={c.get('complete')}"
            prompt += f" mint={full_mint}"
            if desc:
                prompt += f" desc=\"{desc}\""
            if tweet:
                prompt += f" twitter:{tweet}"
            prompt += "\n"
        prompt += "\n"

    prompt += f"""# Your call

Memecoin trading rules (LLM can override all but the hard cap):
- A position is automatically closed at -{int(HARD_STOP_LOSS*100)}% loss OR after {MAX_HOLD_HOURS}h. Other than that, you decide.
- Each buy is 0.1 SOL. Max {MAX_POSITIONS} positions. Keep at least {RESERVE_SOL} SOL in reserve.
- **Memecoins are attention markets.** A good name, a viral X account, an interesting story — these are buy signals, not reasons to skip.
- **New launches are where the alpha is.** A $20k mcap token with a story can do 10x in hours. Top-runners has already-extracted alpha.
- **Don't wait for confirmation.** If you wait for $200k mcap to 'confirm' a $30k token, you'll buy the top.
- **Take some profit at +50%.** But hold longer if the narrative is still strong.
- **It's OK to take 2-3 small losses in a row** if the strategy is right. Catching one 5x in 10 trades pays for all the losers.

Output ONLY valid JSON in this exact shape:
{{
  "exit_decisions": [
    {{"mint": "<full mint from held position, or skip if no held positions>", "action": "hold|sell_all|sell_half", "reasoning": "<1-2 sentences, honest, specific to the data>"}}
  ],
  "entry_decisions": [
    {{"mint": "<full mint from candidates, or skip>", "action": "buy|skip", "reasoning": "<1-2 sentences — name the narrative, the attention signal, the risk>"}}
  ],
  "summary": "<one sentence on the market and what you're doing>"
}}
"""
    return prompt, held, candidates


def get_llm_decisions(prompt):
    response = call_llm(prompt)
    parsed = extract_json(response)
    if not parsed or not isinstance(parsed, dict):
        return None, response, "could not parse JSON"
    return parsed, response, None


# =====================================================================
# Execution
# =====================================================================

def execute_buy(state, mint, token, price_usd, sol_price):
    if state.get("balance_sol", 0) - POSITION_SIZE_SOL < RESERVE_SOL:
        return None, f"would breach reserve ({RESERVE_SOL} SOL)"
    if state.get("balance_sol", 0) < POSITION_SIZE_SOL:
        return None, "insufficient SOL"

    sol_price_usd = sol_price
    usd_value = POSITION_SIZE_SOL * sol_price_usd
    token_amount = usd_value / price_usd if price_usd > 0 else 0
    if token_amount <= 0:
        return None, "could not size position"

    position = {
        "symbol": token.get("symbol", "?"),
        "name": token.get("name", "?"),
        "amount": token_amount,
        "entry_price_usd": price_usd,
        "entry_sol_spent": POSITION_SIZE_SOL,
        "entry_time": iso_now(),
        "entry_usd_value": usd_value,
        "entry_signals": {
            "liquidity_usd": token.get("liquidity_usd"),
            "volume_24h_usd": token.get("volume_h24"),
            "market_cap_usd": token.get("market_cap_usd"),
            "ath_market_cap_usd": token.get("ath_market_cap_usd"),
            "volatility_score": token.get("volatility_score"),
            "boost_mode": token.get("boost_mode"),
            "real_sol_reserves": token.get("real_sol_reserves"),
            "description": token.get("description", "")[:300],
            "twitter": token.get("twitter", ""),
            "source_endpoint": token.get("source_endpoint"),
        },
        "llm_entry": True,
    }
    state["positions"][mint] = position
    state["balance_sol"] = round(state["balance_sol"] - POSITION_SIZE_SOL, 6)
    return position, None


def execute_sell(state, mint, price_usd, fraction, reason):
    pos = state["positions"].get(mint)
    if not pos:
        return None
    sol_price_usd = state.get("last_sol_price_usd", 0)
    sell_amount = pos["amount"] * fraction
    entry_sol_chunk = pos["entry_sol_spent"] * fraction
    usd_at_exit = sell_amount * price_usd
    sol_proceeds = usd_at_exit / sol_price_usd if sol_price_usd > 0 else 0
    pnl_sol = sol_proceeds - entry_sol_chunk
    pnl_pct = (price_usd / pos["entry_price_usd"] - 1) * 100 if pos["entry_price_usd"] > 0 else 0

    trade = {
        "mint": mint,
        "symbol": pos.get("symbol"),
        "name": pos.get("name"),
        "amount_sold": sell_amount,
        "fraction_sold": fraction,
        "entry_time": pos.get("entry_time"),
        "exit_time": iso_now(),
        "entry_price_usd": pos["entry_price_usd"],
        "exit_price_usd": price_usd,
        "entry_sol_for_chunk": round(entry_sol_chunk, 6),
        "exit_sol_received": round(sol_proceeds, 6),
        "pnl_sol": round(pnl_sol, 6),
        "pnl_pct": round(pnl_pct, 2),
        "exit_reason": reason[:200],
        "partial": fraction < 0.999,
    }
    state["trades"].append(trade)
    state["balance_sol"] = round(state["balance_sol"] + sol_proceeds, 6)
    if fraction >= 0.999:
        del state["positions"][mint]
    else:
        pos["amount"] = pos["amount"] * (1 - fraction)
        pos["entry_sol_spent"] = pos["entry_sol_spent"] * (1 - fraction)
    return trade


# =====================================================================
# Git
# =====================================================================

def git_commit_and_push():
    import subprocess
    cwd = WORK_DIR
    try:
        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True, capture_output=True)
        result = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            log("No changes to commit")
            return False
        subprocess.run(
            ["git", "commit", "-m", f"Bot tick @ {now_utc().strftime('%H:%M')} UTC"],
            cwd=cwd, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"], cwd=cwd, check=True, capture_output=True, timeout=60
        )
        log("Pushed")
        return True
    except Exception as e:
        log(f"ERROR git: {e}")
        return False


# =====================================================================
# Main
# =====================================================================

def main():
    log("=== Memecoin bot tick (v4 attention-first) ===")
    state = load_state()
    now = now_utc()

    # 1. Fetch SOL price
    sol_price = None
    try:
        data = http_get_json(f"{DEXSCREENER_BASE}/tokens/{SOL_MINT}")
        pairs = [p for p in (data.get("pairs") or [])
                 if p.get("chainId") == "solana" and _to_float(p.get("priceUsd")) > 0]
        if pairs:
            pairs.sort(key=lambda p: _to_float((p.get("liquidity") or {}).get("usd")), reverse=True)
            sol_price = _to_float(pairs[0]["priceUsd"])
    except Exception as e:
        log(f"ERROR: SOL price fetch failed: {e}")
        sys.exit(1)
    state["last_sol_price_usd"] = sol_price
    log(f"SOL: ${sol_price:.2f}")

    # 2. Fetch freshest tokens (the actual opportunity feed)
    fresh = fetch_pumpfun_freshest(limit=25)
    top_runners = fetch_pumpfun_top_runners(limit=15)

    # 3. Dedupe + combine, preserving rich data
    by_mint = {}
    for t in fresh:
        by_mint[t["mint"]] = t
    for t in top_runners:
        if t["mint"] not in by_mint:
            by_mint[t["mint"]] = t
    tokens = list(by_mint.values())
    log(f"Total candidate tokens: {len(tokens)} (fresh: {len(fresh)}, top-runners: {len(top_runners)}, deduped: {len(tokens)})")

    # 4. Detect NEW mints (alpha!)
    last_seen = load_last_seen_mints()
    current_mints = {t["mint"] for t in tokens}
    new_mints = current_mints - last_seen
    new_launch_alert = ""
    if new_mints:
        log(f"🆕 {len(new_mints)} NEW mints detected since last tick")
    save_last_seen_mints(current_mints)

    # 5. Enrich with DexScreener + compute bonding curve price for fresh tokens
    mints = [t["mint"] for t in tokens]
    dex_data = fetch_dexscreener_for_mints(mints)
    for t in tokens:
        pair = dex_data.get(t["mint"])
        if pair:
            t["price_usd"] = pair.get("priceUsd")
            t["price_sol"] = pair.get("priceNative")
            t["liquidity_usd"] = _to_float((pair.get("liquidity") or {}).get("usd"))
            t["volume_h24"] = _to_float((pair.get("volume") or {}).get("h24"))
            t["price_change_h24"] = _to_float((pair.get("priceChange") or {}).get("h24"))
            t["price_change_h1"] = _to_float((pair.get("priceChange") or {}).get("h1"))
            t["price_change_m5"] = _to_float((pair.get("priceChange") or {}).get("m5"))
            t["pair_url"] = pair.get("url")
            t["dex_id"] = pair.get("dexId")
            t["pair_address"] = pair.get("pairAddress")
        elif t.get("complete"):
            # Completed but no DexScreener pair — fall back to bonding curve price
            pass
        # For fresh tokens on the bonding curve, compute the price ourselves.
        # If neither DexScreener nor bonding-curve price is available, skip.
        if not t.get("price_usd"):
            vsr = _to_float(t.get("virtual_sol_reserves"))  # in SOL
            vtr = _to_float(t.get("virtual_token_reserves"))  # in tokens
            if vsr > 0 and vtr > 0:
                # price in SOL per token
                price_sol = vsr / vtr
                t["price_sol"] = price_sol
                t["price_usd"] = price_sol * sol_price
                t["price_source"] = "bonding-curve"

    # 5b. Fetch current prices for HELD positions (separate from new launches —
    # held tokens may have aged out of pump.fun's new-launches feed).
    held_mints = list(state.get("positions", {}).keys())
    held_dex_data = fetch_dexscreener_for_mints(held_mints)
    held_prices = {}  # mint -> {price_usd, change_24h, change_1h, liq, vol_24h, source}
    for mint, pos in state.get("positions", {}).items():
        pair = held_dex_data.get(mint)
        ds_liq = _to_float((pair.get("liquidity") or {}).get("usd")) if pair else 0
        ds_price = _to_float(pair.get("priceUsd")) if pair else 0

        if ds_price > 0 and ds_liq > 0:
            # Best case: real DEX with confirmed liquidity
            held_prices[mint] = {
                "price_usd": ds_price,
                "change_h24": _to_float((pair.get("priceChange") or {}).get("h24")),
                "change_h1": _to_float((pair.get("priceChange") or {}).get("h1")),
                "liquidity_usd": ds_liq,
                "volume_h24": _to_float((pair.get("volume") or {}).get("h24")),
                "dex_id": pair.get("dexId"),
                "source": "dexscreener",
            }
        else:
            # No real DEX liquidity. Try pump.fun bonding-curve (real_sol_reserves as liquidity proxy).
            coin = fetch_pumpfun_coin(mint)
            price_usd = 0
            chg24 = 0
            real_sol = 0
            complete = False
            if coin:
                vsr = _to_float(coin.get("virtual_sol_reserves")) / 1e9
                vtr = _to_float(coin.get("virtual_token_reserves")) / 1e6
                if vsr > 0 and vtr > 0:
                    price_sol = vsr / vtr
                    price_usd = price_sol * sol_price
                real_sol = _to_float(coin.get("real_sol_reserves")) / 1e9
                complete = bool(coin.get("complete"))
            # Effective liquidity: real_sol for bonding curve tokens, 0 if no data
            effective_liq = real_sol * sol_price
            held_prices[mint] = {
                "price_usd": price_usd if price_usd > 0 else ds_price,
                "change_h24": chg24,
                "change_h1": 0,
                "liquidity_usd": effective_liq,
                "volume_h24": _to_float((pair.get("volume") or {}).get("h24")) if pair else 0,
                "dex_id": "pumpfun" if not complete else pair.get("dexId") if pair else None,
                "source": "bonding-curve" if price_usd > 0 else ("dexscreener-no-liq" if ds_price > 0 else "missing"),
                "complete": complete,
                "real_sol_reserves": real_sol,
            }
    if held_mints:
        log(f"Fetched prices for {len(held_mints)} held positions ({sum(1 for v in held_prices.values() if v['price_usd'] > 0)} with valid price)")

    # 6. Save watchlist for the dashboard
    WATCHLIST_PATH.write_text(json.dumps({
        "fetched_at": iso_now(),
        "sol_price_usd": sol_price,
        "tokens": tokens,
        "new_mints": list(new_mints),
    }, indent=2, ensure_ascii=False))

    # 7. Hard max-hold check (LLM can't hold forever)
    for mint, pos in list(state.get("positions", {}).items()):
        if not pos.get("entry_time"):
            continue
        held_hours = (now - parse_iso(pos["entry_time"])).total_seconds() / 3600
        if held_hours >= MAX_HOLD_HOURS:
            token = next((t for t in tokens if t["mint"] == mint), None)
            if token and _to_float(token.get("price_usd")) > 0:
                trade = execute_sell(state, mint, _to_float(token["price_usd"]), 1.0, f"max-hold {MAX_HOLD_HOURS}h reached")
                if trade:
                    log(f"FORCED EXIT: ${trade['symbol']} after {MAX_HOLD_HOURS}h — PnL {trade['pnl_pct']:+.1f}%")
                    append_decision({
                        "action": "sell",
                        "details": f"[max-hold] ${trade['symbol']} closed at ${trade['exit_price_usd']:.6g} | P&L: {trade['pnl_pct']:+.1f}%",
                        "reason": f"Hard {MAX_HOLD_HOURS}h cap",
                    })

    # 8. Hard stop-loss (-50%) — non-negotiable
    for mint, pos in list(state.get("positions", {}).items()):
        # Hard stop fires regardless of whether mint is in fresh-tokens list.
        # Use held_prices (always populated for held positions).
        hp = held_prices.get(mint) or {}
        cur_price = _to_float(hp.get("price_usd"))
        if cur_price <= 0:
            # Try fresh tokens as fallback
            token = next((t for t in tokens if t["mint"] == mint), None)
            if token:
                cur_price = _to_float(token.get("price_usd"))
            if cur_price <= 0:
                continue
        entry_price = _to_float(pos.get("entry_price_usd"))
        if entry_price > 0 and cur_price / entry_price <= (1 - HARD_STOP_LOSS):
            trade = execute_sell(state, mint, cur_price, 1.0, f"hard-stop -{int(HARD_STOP_LOSS*100)}%")
            if trade:
                log(f"HARD STOP: ${trade['symbol']} closed at -{int(HARD_STOP_LOSS*100)}%")
                append_decision({
                    "action": "sell",
                    "details": f"[hard-stop] ${trade['symbol']} closed at ${cur_price:.6g} | P&L: {trade['pnl_pct']:+.1f}%",
                    "reason": f"Hard -{int(HARD_STOP_LOSS*100)}% stop",
                })

    # 8b. Auto take-profit — lock in gains (non-negotiable)
    for mint, pos in list(state.get("positions", {}).items()):
        if mint not in state.get("positions", {}):
            continue  # already closed by hard-stop
        # Held positions often NOT in the fresh tokens list — use held_prices directly
        hp = held_prices.get(mint) or {}
        cur_price = _to_float(hp.get("price_usd"))
        entry_price = _to_float(pos.get("entry_price_usd"))
        if cur_price <= 0 or entry_price <= 0:
            continue
        pnl_pct = (cur_price / entry_price - 1) * 100
        log(f"TP-check: ${pos.get('symbol')} pnl={pnl_pct:+.1f}% cur={cur_price:.10f} entry={entry_price:.10f}")
        # Take-profit tiers
        if pnl_pct >= 300:
            tp_action = "TP +500% (full)"
            tp_fraction = 1.0
        elif pnl_pct >= 200:
            tp_action = "TP +200% (75%)"
            tp_fraction = 0.75
        elif pnl_pct >= 100:
            tp_action = "TP +100% (50%)"
            tp_fraction = 0.5
        elif pnl_pct >= 30:
            tp_action = "TP +30% (25%)"
            tp_fraction = 0.25
        else:
            continue
        if pos.get("amount", 0) <= 0:
            continue
        trade = execute_sell(state, mint, cur_price, tp_fraction, f"auto-{tp_action}")
        if trade:
            log(f"TAKE PROFIT: ${trade['symbol']} {tp_action} — {trade['pnl_pct']:+.1f}%")
            append_decision({
                "action": "sell",
                "details": f"[{tp_action}] ${trade['symbol']} at ${cur_price:.6g} | P&L: {trade['pnl_pct']:+.1f}%",
                "reason": f"Auto take-profit at {pnl_pct:+.1f}%",
            })

    # 8c. Stale-position exit — flat for >30 min, cut regardless of P&L
    for mint, pos in list(state.get("positions", {}).items()):
        if mint not in state.get("positions", {}):
            continue
        if not pos.get("entry_time"):
            continue
        held_hours = (now - parse_iso(pos["entry_time"])).total_seconds() / 3600
        if held_hours < 0.5:  # 30 min
            continue
        hp = held_prices.get(mint) or {}
        cur_price = _to_float(hp.get("price_usd"))
        if cur_price <= 0:
            continue
        entry_price = _to_float(pos.get("entry_price_usd"))
        pnl_pct = (cur_price / entry_price - 1) * 100 if entry_price > 0 else 0
        if pnl_pct >= 20:
            continue  # up big, let it run
        # Held >30 min and not up big → stale → exit
        trade = execute_sell(state, mint, cur_price, 1.0, f"stale-position exit ({held_hours:.1f}h held, {pnl_pct:+.1f}%)")
        if trade:
            log(f"STALE EXIT: ${trade['symbol']} held {held_hours:.1f}h at {trade['pnl_pct']:+.1f}%")
            append_decision({
                "action": "sell",
                "details": f"[stale] ${trade['symbol']} at ${cur_price:.6g} | P&L: {trade['pnl_pct']:+.1f}%",
                "reason": f"Held {held_hours:.1f}h with no momentum",
            })

    # 9. Compute portfolio
    portfolio = compute_portfolio_value(state, sol_price, dex_data)
    today_pnl = compute_today_realized_pnl(state)
    log(f"Portfolio: ${portfolio['total_value_usd']:.2f} | Today: {today_pnl:+.4f} SOL")

    daily_loss_breached = today_pnl < -DAILY_MAX_LOSS_SOL

    # 10. Build prompt
    prompt, held, candidates = build_decision_prompt(
        state, sol_price,
        {"tokens": tokens},
        portfolio, today_pnl, new_mints, held_prices,
    )

    # 11. Throttle: skip LLM if idle and last brief was recent
    should_call_llm = True
    if not held and not new_mints and ALWAYS_LLM_TICK:
        last_brief = state.get("last_llm_brief_at")
        if last_brief:
            last_dt = parse_iso(last_brief)
            if last_dt and (now - last_dt).total_seconds() < LLM_BRIEF_INTERVAL_MIN * 60:
                log(f"No positions, no new mints, last LLM brief {(now-last_dt).total_seconds():.0f}s ago — skipping")
                should_call_llm = False

    if not should_call_llm:
        state["portfolio_value_usd"] = portfolio["total_value_usd"]
        state["last_updated"] = iso_now()
        state["recent_decisions"] = load_recent_decisions(max_n=20)
        state["held_prices"] = held_prices
        save_state(state)
        git_commit_and_push()
        return

    # 12. Call LLM
    log(f"Calling LLM (held={len(held)}, new_mints={len(new_mints)}, total_candidates={len(candidates)})...")
    try:
        decisions, raw_response, parse_err = get_llm_decisions(prompt)
    except Exception as e:
        log(f"ERROR: LLM call failed: {e}")
        decisions, raw_response, parse_err = None, str(e), "llm call failed"

    log_full_decision(prompt, raw_response, "tick", f"held={len(held)} new_mints={len(new_mints)}")
    state["last_llm_brief_at"] = iso_now()

    if not decisions:
        log(f"WARN: {parse_err} — holding all, no entries")
        log(f"Raw (first 300): {raw_response[:300]}")
        append_decision({
            "action": "observe",
            "details": f"LLM call failed: {parse_err}",
            "reason": "bot cannot decide, holding positions",
        })
        state["portfolio_value_usd"] = portfolio["total_value_usd"]
        state["last_updated"] = iso_now()
        state["recent_decisions"] = load_recent_decisions(max_n=20)
        state["held_prices"] = held_prices
        save_state(state)
        git_commit_and_push()
        return

    # 13. Execute exit decisions
    exits_made = 0
    for dec in decisions.get("exit_decisions", []) or []:
        if not isinstance(dec, dict):
            continue
        target_mint_prefix = dec.get("mint", "")
        action = dec.get("action", "").lower()
        reasoning = dec.get("reasoning", "")
        target_mint = None
        for full_mint in state.get("positions", {}):
            if full_mint.startswith(target_mint_prefix[:10]):
                target_mint = full_mint
                break
        if not target_mint:
            continue
        # Get current price from held_prices (always fetched) — fallback to watchlist
        hprice = held_prices.get(target_mint) or {}
        cur_price = hprice.get("price_usd") or 0
        if cur_price <= 0:
            token = next((t for t in tokens if t["mint"] == target_mint), None)
            if token:
                cur_price = _to_float(token.get("price_usd"))
        if cur_price <= 0:
            log(f"WARN: exit skipped for ${state['positions'][target_mint].get('symbol', '?')} — no current price")
            continue
        if action == "hold":
            continue
        fraction = 1.0 if action == "sell_all" else 0.5 if action == "sell_half" else None
        if fraction is None:
            continue
        # Liquidity-aware exit cap: if position > 30% of pool, sell only what fits.
        pos = state["positions"].get(target_mint)
        pos_value = (pos.get("amount", 0) * cur_price) if pos else 0
        liq = _to_float(hprice.get("liquidity_usd"))
        if liq > 0 and pos_value > 0:
            current_pct = pos_value / liq * 100
            if current_pct > 30:
                # Sell only enough to bring position to 25% of pool
                target_value = liq * 0.25
                keep_value = min(target_value, pos_value * 0.5)  # never keep more than half
                safe_fraction = max(0.1, (pos_value - keep_value) / pos_value)
                if safe_fraction < fraction:
                    log(f"LIQUIDITY CAP: ${pos.get('symbol')} was sell {action} but pos={current_pct:.0f}% of pool — capping at {safe_fraction*100:.0f}% to avoid -90% slippage")
                    fraction = safe_fraction
        trade = execute_sell(state, target_mint, cur_price, fraction, f"LLM: {action} — {reasoning[:150]}")
        if trade:
            exits_made += 1
            action_label = "PARTIAL" if trade.get("partial") else "FULL"
            log(f"{action_label} SELL ${trade['symbol']}: {trade['pnl_pct']:+.1f}% — {reasoning[:80]}")
            append_decision({
                "action": "sell",
                "details": f"[{action_label}][LLM] ${trade['symbol']} at ${cur_price:.6g} | P&L: {trade['pnl_pct']:+.1f}%",
                "reason": reasoning,
            })

    # 14. Execute entry decisions
    if daily_loss_breached:
        log(f"Daily loss cap hit ({today_pnl:+.4f} < -{DAILY_MAX_LOSS_SOL} SOL) — no new entries")
    else:
        for dec in decisions.get("entry_decisions", []) or []:
            if not isinstance(dec, dict):
                continue
            target_mint_prefix = dec.get("mint", "")
            action = dec.get("action", "").lower()
            reasoning = dec.get("reasoning", "")
            if action != "buy":
                continue
            target_mint = None
            for c in candidates:
                if c["mint"].startswith(target_mint_prefix[:10]):
                    target_mint = c["mint"]
                    break
            if not target_mint:
                log(f"DEBUG: LLM wanted to buy {target_mint_prefix[:20]} but no candidate matched. Available: {[c['mint'][:10] for c in candidates]}")
                continue
            if target_mint in state.get("positions", {}):
                continue
            if len(state.get("positions", {})) >= MAX_POSITIONS:
                break
            token = next((t for t in tokens if t["mint"] == target_mint), None)
            if not token or _to_float(token.get("price_usd")) <= 0:
                log(f"DEBUG: {target_mint[:10]} matched but no price (price_usd={token.get('price_usd') if token else 'NO TOKEN'})")
                continue
            # Liquidity gate: skip if effective liquidity < 5x position size.
            # Position of 0.1 SOL (~$10) needs ≥$50 pool liquidity to exit safely.
            pos_value_usd = POSITION_SIZE_SOL * sol_price
            eff_liq = _to_float(token.get("liquidity_usd"))
            if eff_liq <= 0:
                # Try to fetch pump.fun data for liquidity proxy
                coin = fetch_pumpfun_coin(target_mint)
                if coin:
                    real_sol = _to_float(coin.get("real_sol_reserves")) / 1e9
                    eff_liq = real_sol * sol_price
                    token["liquidity_usd"] = eff_liq
                    token["real_sol_reserves"] = real_sol
                    if not token.get("price_usd"):
                        vsr = _to_float(coin.get("virtual_sol_reserves")) / 1e9
                        vtr = _to_float(coin.get("virtual_token_reserves")) / 1e6
                        if vsr > 0 and vtr > 0:
                            token["price_usd"] = (vsr / vtr) * sol_price
            if eff_liq < pos_value_usd * 5:
                log(f"LIQUIDITY GATE: ${token.get('symbol')} rejected — pool ${eff_liq:.0f} < 5x position ${pos_value_usd:.2f}")
                continue
            # === CoinCLIP-style viability filter (research: arXiv 2412.07591) ===
            # Skip tokens that look like low-quality/quick-flips:
            #  - Description < 50 chars (lazy project)
            #  - No twitter handle (community signal missing)
            #  - Very low liquidity (<$2k) — too easy to dump
            desc = (token.get("description") or token.get("desc") or "").strip()
            twitter = (token.get("twitter") or "").strip()
            if len(desc) < 50:
                log(f"VIABILITY GATE: ${token.get('symbol')} rejected — description too short ({len(desc)} chars)")
                continue
            if not twitter and eff_liq < 3000:
                log(f"VIABILITY GATE: ${token.get('symbol')} rejected — no twitter AND low liquidity (${eff_liq:.0f})")
                continue
            # === ME2F fragility filter (research: arXiv 2512.00377) ===
            # ME2F found political/celebrity-themed tokens are the MOST fragile.
            # Top-100 holders often >90%, sentiment amplification 20%+, volatility extreme.
            # Filter: block names that scream "celebrity/political token" = high fragility
            FRAGILITY_KEYWORDS = [
                "trump", "biden", "harris", "musk", "elon", "cz", "binance",
                "melania", "libra", "ivanka", "tiffany", "barron",
                "kanye", "ye", "swift", "beyonce", "taylor",
                "putin", "xi", "jinping", "modi", "zelensky",
                "celebrity", "political", "president", "official", "government",
            ]
            sym_lower = (token.get("symbol") or "").lower()
            name_lower = (token.get("name") or "").lower()
            desc_lower = desc.lower()
            matched_kw = next((kw for kw in FRAGILITY_KEYWORDS if kw in sym_lower or kw in name_lower or kw in desc_lower), None)
            if matched_kw:
                log(f"FRAGILITY GATE: ${token.get('symbol')} rejected — matches '{matched_kw}' (ME2F: political/celebrity = high fragility)")
                continue
            # Dedup by symbol within tick — LLM sometimes picks same mint twice
            existing_syms = {p.get("symbol") for p in state.get("positions", {}).values()}
            if token.get("symbol") in existing_syms:
                log(f"DUPE SKIP: ${token.get('symbol')} already held")
                continue
            pos, err = execute_buy(state, target_mint, token, _to_float(token["price_usd"]), sol_price)
            if pos:
                log(f"LLM BUY ${pos['symbol']}: ${pos['amount']:.4f} tokens @ ${pos['entry_price_usd']:.6g}")
                log(f"  Reasoning: {reasoning[:120]}")
                append_decision({
                    "action": "buy",
                    "details": f"[LLM] ${pos['symbol']} at ${pos['entry_price_usd']:.6g}, spent {POSITION_SIZE_SOL} SOL",
                    "reason": reasoning,
                })
            elif err:
                log(f"Buy blocked: {err}")

    # 15. Save + push (ALWAYS, not just when no exits)
    state["portfolio_value_usd"] = compute_portfolio_value(state, sol_price, dex_data)["total_value_usd"]
    state["last_updated"] = iso_now()
    state["recent_decisions"] = load_recent_decisions(max_n=20)
    state["held_prices"] = held_prices  # mint -> {price_usd, change_24h, ...}
    state["trade_stats"] = compute_trade_stats(state)
    save_state(state)
    log(f"State: {len(state.get('positions', {}))} positions, {len(state.get('trades', []))} trades")
    git_commit_and_push()


if __name__ == "__main__":
    main()