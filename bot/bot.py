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
import urllib.error
import urllib.request
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

# === APIs ===
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
PUMPFUN_TOP_RUNNERS = "https://frontend-api-v3.pump.fun/coins/top-runners"
PUMPFUN_RECOMMENDED = "https://frontend-api-v3.pump.fun/coins/recommended"
# Newest launches: sort by created_timestamp DESC. Returns truly fresh tokens.
PUMPFUN_NEW_LAUNCHES = "https://frontend-api-v3.pump.fun/coins?limit=30&offset=0&sort=created_timestamp&order=DESC&includeNsfw=false"
SOL_MINT = "So11111111111111111111111111111111111111112"

# === Strategy parameters (safeguards — LLM can't override) ===
POSITION_SIZE_SOL = 0.1
MAX_POSITIONS = 5
MAX_HOLD_HOURS = 72
HARD_STOP_LOSS = 0.5        # -50% hard cap, beyond this we MUST exit
DAILY_MAX_LOSS_SOL = 0.4    # if today's realized < -0.4 SOL, no new entries
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
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


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
        "response": response[:2000],
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
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    return None


# =====================================================================
# Build the prompt — ATTENTION FIRST
# =====================================================================

def build_decision_prompt(state, sol_price, watchlist_data, portfolio, today_pnl, new_mints):
    """v4: LLM gets narrative context + new-launch alerts."""

    positions = state.get("positions", {})

    # === Held positions with context ===
    held = []
    for mint, pos in positions.items():
        token = next((t for t in watchlist_data["tokens"] if t["mint"] == mint), None)
        if not token:
            continue
        cur_price = _to_float(token.get("price_usd"))
        entry_price = _to_float(pos.get("entry_price_usd"))
        pnl_pct = ((cur_price / entry_price - 1) * 100) if cur_price > 0 and entry_price > 0 else 0
        held_hours = 0
        if pos.get("entry_time"):
            held_hours = (now_utc() - parse_iso(pos["entry_time"])).total_seconds() / 3600
        held.append({
            "symbol": pos.get("symbol"),
            "mint": mint,
            "amount_tokens": pos.get("amount"),
            "entry_price_usd": entry_price,
            "current_price_usd": cur_price,
            "pnl_pct": round(pnl_pct, 1),
            "held_hours": round(held_hours, 1),
            "volatility_score": token.get("volatility_score"),
            "boost_mode": token.get("boost_mode"),
            "real_sol_reserves": token.get("real_sol_reserves"),
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

    # === Recent trades summary ===
    trades = state.get("trades", [])
    recent_trades = trades[-5:] if trades else []
    wins = sum(1 for t in trades if _to_float(t.get("pnl_sol", 0)) > 0)
    losses = len(trades) - wins

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

# Current state
- SOL free: {state.get('balance_sol', 0):.4f} SOL (${state.get('balance_sol', 0) * sol_price:.2f})
- Open positions: {len(held)}/{MAX_POSITIONS}
- Total portfolio: ${portfolio['total_value_usd']:.2f}
- Today's realized P&L: {today_pnl:+.4f} SOL
- Daily target: +20% (0.4 SOL). Hard daily loss cap: -{DAILY_MAX_LOSS_SOL} SOL (no new entries if exceeded)
- All-time: {len(trades)} trades, {wins}W/{losses}L
- **Hard cap on any single position loss: -{int(HARD_STOP_LOSS*100)}%. LLM cannot override this.**

# Recent trades (last 5)
""" + "\n".join([
        f"  - {t.get('symbol')} {t.get('pnl_pct', 0):+.1f}% via {(t.get('exit_reason') or '')[:60]}"
        for t in recent_trades
    ]) + "\n"
    prompt += new_launch_alert
    if held:
        prompt += "\n# Held positions (decide: hold / sell_all / sell_half)\n"
        for h in held:
            prompt += f"  - ${h['symbol']} entry ${h['entry_price_usd']:.6g} now ${h['current_price_usd']:.6g} = {h['pnl_pct']:+.1f}%, held {h['held_hours']:.1f}h, real_sol={h['real_sol_reserves']:.2f}\n"
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
            prompt += f"  {flag}${c['symbol']:10} ({c['name'][:24]:24}) age={str(age)+'min':>8} mcap=${mcap:>9,.0f} bond={bonding:.0f}% complete={c.get('complete')}"
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
    if new_mints:
        log(f"🆕 {len(new_mints)} NEW mints detected since last tick")
    save_last_seen_mints(current_mints)

    # 5. Enrich with DexScreener
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
        token = next((t for t in tokens if t["mint"] == mint), None)
        if not token:
            continue
        cur_price = _to_float(token.get("price_usd"))
        if cur_price <= 0:
            continue
        entry_price = _to_float(pos.get("entry_price_usd"))
        if entry_price > 0 and cur_price / entry_price <= (1 - HARD_STOP_LOSS):
            trade = execute_sell(state, mint, cur_price, 1.0, f"hard-stop -{int(HARD_STOP_LOSS*100)}%")
            if trade:
                log(f"HARD STOP: ${trade['symbol']} closed at -50% — PnL {trade['pnl_pct']:+.1f}%")
                append_decision({
                    "action": "sell",
                    "details": f"[hard-stop] ${trade['symbol']} closed at ${cur_price:.6g} | P&L: {trade['pnl_pct']:+.1f}%",
                    "reason": f"Hard -{int(HARD_STOP_LOSS*100)}% stop",
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
        portfolio, today_pnl, new_mints,
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
        token = next((t for t in tokens if t["mint"] == target_mint), None)
        if not token or _to_float(token.get("price_usd")) <= 0:
            continue
        cur_price = _to_float(token["price_usd"])
        if action == "hold":
            continue
        fraction = 1.0 if action == "sell_all" else 0.5 if action == "sell_half" else None
        if fraction is None:
            continue
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
            if not target_mint or target_mint in state.get("positions", {}):
                continue
            if len(state.get("positions", {})) >= MAX_POSITIONS:
                break
            token = next((t for t in tokens if t["mint"] == target_mint), None)
            if not token or _to_float(token.get("price_usd")) <= 0:
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

    # 15. Save + push
    if exits_made == 0 and len(state.get("positions", {})) == len(held):
        summary = decisions.get("summary", "no summary")
        append_decision({
            "action": "observe",
            "details": f"LLM tick: {exits_made} exits, no new entries. {len(state.get('positions', {}))} positions held",
            "reason": summary,
        })

    state["portfolio_value_usd"] = compute_portfolio_value(state, sol_price, dex_data)["total_value_usd"]
    state["last_updated"] = iso_now()
    state["recent_decisions"] = load_recent_decisions(max_n=20)
    save_state(state)
    log(f"State: {len(state.get('positions', {}))} positions, {len(state.get('trades', []))} trades")
    git_commit_and_push()


if __name__ == "__main__":
    main()