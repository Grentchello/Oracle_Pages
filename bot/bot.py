#!/usr/bin/env python3
"""
Memecoin Trading Bot — v3 (LLM-decided)

Replaces rules-based exits with LLM judgment. Entry uses basic gates + LLM review.
Every decision is logged with the LLM's reasoning — the actual learning artifact.

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

# === APIs ===
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
PUMPFUN_TOP_RUNNERS = "https://frontend-api-v3.pump.fun/coins/top-runners"
SOL_MINT = "So11111111111111111111111111111111111111112"

# === Strategy parameters (safeguards — LLM can't override) ===
POSITION_SIZE_SOL = 0.1
MAX_POSITIONS = 5
MIN_LIQUIDITY_USD = 5000
MIN_VOLUME_24H_USD = 10000
MAX_HOLD_HOURS = 72          # hard max — even LLM can't hold forever
DAILY_MAX_LOSS_SOL = 0.3      # if today's realized < -0.3 SOL, no new entries
RESERVE_SOL = 0.1             # never go below this in SOL — keep some dry powder

# Allow mild downturns in entry gate — top-runners in -15% pullback are often buyable
MIN_PRICE_CHANGE_24H = -15.0

# Run an LLM "market read" tick even when there's nothing to do,
# but throttle: every LLM_BRIEF_INTERVAL_MIN when idle, every tick when holding.
ALWAYS_LLM_TICK = True
LLM_BRIEF_INTERVAL_MIN = 5  # how often to call LLM when there's nothing to do

# === LLM config ===
HERMES_CLI = "/opt/hermes/.venv/bin/hermes"
LLM_TIMEOUT_SECONDS = 90

# === Network ===
TIMEOUT = 15
USER_AGENT = "oracle-vault-memecoin-bot/3.0"


# =====================================================================
# Utilities (unchanged)
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
# Data fetchers (unchanged)
# =====================================================================

def fetch_sol_price_usd():
    try:
        data = http_get_json(f"{DEXSCREENER_BASE}/tokens/{SOL_MINT}")
        pairs = [p for p in (data.get("pairs") or [])
                 if p.get("chainId") == "solana" and _to_float(p.get("priceUsd")) > 0]
        if not pairs:
            return None
        pairs.sort(key=lambda p: _to_float((p.get("liquidity") or {}).get("usd")), reverse=True)
        return _to_float(pairs[0]["priceUsd"])
    except Exception as e:
        log(f"WARN: SOL price fetch failed: {e}")
        return None


def fetch_pumpfun_top_runners(limit=30):
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
                "ath_market_cap_usd": _to_float(coin.get("ath_market_cap")),
                "last_trade_ts": coin.get("last_trade_timestamp"),
                "complete": coin.get("complete", False),
            })
        return out
    except Exception as e:
        log(f"WARN: pump.fun fetch failed: {e}")
        return []


def fetch_dexscreener_for_mints(mints):
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
        return {
            "balance_sol": 2.0,
            "positions": {},
            "trades": [],
            "bot_version": "3.0-llm",
        }
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return _fresh_state()


def _fresh_state():
    return {
        "balance_sol": 2.0,
        "positions": {},
        "trades": [],
        "bot_version": "3.0-llm",
    }


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def append_decision(decision):
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DECISIONS_PATH.exists():
        DECISIONS_PATH.write_text(
            "# Bot Decisions Log\n\n"
            "> v3 — LLM-decided trading. Each entry shows bot action + reasoning.\n\n"
        )
    ts = now_utc().strftime("%Y-%m-%d %H:%M UTC")
    line = f"## [{ts}] {decision['action']} | {decision.get('details', '')}\n"
    if decision.get("reason"):
        line += f"- **Reasoning:** {decision['reason']}\n"
    if decision.get("model"):
        line += f"- Model: {decision['model']}"
    if decision.get("data"):
        line += f"\n- Data: `{json.dumps(decision['data'], ensure_ascii=False)[:500]}`"
    line += "\n\n"
    with open(DECISIONS_PATH, "a") as f:
        f.write(line)


def log_full_decision(prompt, response, action, target):
    """Persist full LLM call for later review."""
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
    # Keep last 100
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
            current = {
                "time": m.group(1),
                "action": m.group(2),
                "details": m.group(3),
                "reason": "",
            }
        elif current:
            rm = re.match(r"^- \*\*Reasoning:\*\* (.*)$", line)
            if rm:
                current["reason"] = rm.group(1)
    if current:
        decisions.append(current)
    return decisions[-max_n:]


def build_watchlist_state(sol_price, top_runners, dex_data):
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
            entry["price_change_h1"] = (pair.get("priceChange") or {}).get("h1")
            entry["price_change_m5"] = (pair.get("priceChange") or {}).get("m5")
            entry["pair_url"] = pair.get("url")
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
# LLM — the new brain
# =====================================================================

def call_llm(prompt, max_seconds=LLM_TIMEOUT_SECONDS):
    """Call the gateway's LLM. Returns raw text response or raises."""
    try:
        result = subprocess.run(
            [HERMES_CLI, "chat", "-q", prompt, "-Q",
             "--max-turns", "1", "--run-budget", str(max_seconds),
             "--ignore-rules", "--safe-mode",  # skip extra tool loading
             "-t", "terminal",  # only need terminal for tool access
             ],
            capture_output=True, text=True, timeout=max_seconds + 30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"hermes chat failed (rc={result.returncode}): {result.stderr[:300]}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"LLM call timed out after {max_seconds}s")


def extract_json(text):
    """Find JSON in LLM output (handles ```json blocks, surrounding prose)."""
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try code-fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try to find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    return None


# =====================================================================
# Decisions — the LLM makes them
# =====================================================================

def build_decision_prompt(state, sol_price, watchlist_data, portfolio_value, today_pnl):
    """Build the prompt for the LLM to make entry + exit decisions."""
    positions = state.get("positions", {})
    held = []
    for mint, pos in positions.items():
        token = next((t for t in watchlist_data["tokens"] if t["mint"] == mint), None)
        if not token:
            continue
        cur_price = _to_float(token.get("price_usd"))
        entry_price = _to_float(pos.get("entry_price_usd"))
        if cur_price > 0 and entry_price > 0:
            pnl_pct = (cur_price / entry_price - 1) * 100
        else:
            pnl_pct = 0
        held_hours = 0
        if pos.get("entry_time"):
            held_hours = (now_utc() - parse_iso(pos["entry_time"])).total_seconds() / 3600
        held.append({
            "symbol": pos.get("symbol"),
            "mint": mint[:8] + "…",
            "amount_tokens": pos.get("amount"),
            "entry_price_usd": entry_price,
            "current_price_usd": cur_price,
            "pnl_pct": round(pnl_pct, 1),
            "held_hours": round(held_hours, 1),
            "chg_24h": token.get("price_change_h24"),
            "chg_1h": token.get("price_change_h1"),
            "liquidity_usd": token.get("liquidity_usd"),
            "volume_24h_usd": token.get("volume_h24"),
            "mcap_usd": token.get("market_cap_usd"),
            "ath_mcap_usd": token.get("ath_market_cap_usd"),
        })

    # Candidate entries — only show ones passing basic gates
    held_mints = set(positions.keys())
    candidates = []
    for token in watchlist_data.get("tokens", []):
        if token["mint"] in held_mints:
            continue
        liq = _to_float(token.get("liquidity_usd"))
        vol = _to_float(token.get("volume_h24"))
        chg24 = _to_float(token.get("price_change_h24"))
        if liq < MIN_LIQUIDITY_USD or vol < MIN_VOLUME_24H_USD or chg24 < MIN_PRICE_CHANGE_24H:
            continue
        candidates.append({
            "symbol": token.get("symbol"),
            "name": token.get("name"),
            "mint": token.get("mint", "")[:8] + "…",
            "price_usd": _to_float(token.get("price_usd")),
            "chg_24h": chg24,
            "chg_1h": _to_float(token.get("price_change_h1")),
            "liquidity_usd": liq,
            "volume_24h_usd": vol,
            "mcap_usd": _to_float(token.get("market_cap_usd")),
            "ath_mcap_usd": _to_float(token.get("ath_market_cap_usd")),
        })
    candidates = candidates[:8]  # top 8 by some metric — let LLM sort

    # Stats
    trades = state.get("trades", [])
    recent_trades = trades[-5:] if trades else []
    wins = sum(1 for t in trades if _to_float(t.get("pnl_sol", 0)) > 0)
    losses = len(trades) - wins

    prompt = f"""You are a memecoin trading bot. Manage a 2 SOL paper portfolio. Be honest and skeptical.

# Current state
- SOL free: {state.get('balance_sol', 0):.4f} SOL (${state.get('balance_sol', 0) * sol_price:.2f})
- Open positions: {len(held)}/{MAX_POSITIONS}
- Total portfolio: ${portfolio_value['total_value_usd']:.2f}
- Today's realized P&L: {today_pnl:+.4f} SOL
- Daily target: +20% (0.4 SOL). Daily loss cap: -{DAILY_MAX_LOSS_SOL} SOL (no new entries if exceeded)
- All-time: {len(trades)} trades, {wins}W/{losses}L

# Recent trades (last 5)
""" + "\n".join([
        f"  {t.get('symbol')} {t.get('pnl_pct', 0):+.1f}% via {t.get('exit_reason', '?')[:40]} — {(t.get('post_mortem') or {}).get('diagnosis', '')[:100]}"
        for t in recent_trades
    ]) + "\n\n"

    if held:
        prompt += "# Held positions (decide: hold / sell-all / sell-half)\n"
        for h in held:
            prompt += f"- ${h['symbol']} ({h['mint']}) entry ${h['entry_price_usd']:.6g} now ${h['current_price_usd']:.6g} = {h['pnl_pct']:+.1f}%, held {h['held_hours']:.1f}h, 24h_chg={h['chg_24h']}%, 1h_chg={h['chg_1h']}%, liq=${h['liquidity_usd']:.0f}, vol24=${h['volume_24h_usd']:.0f}, mcap=${h['mcap_usd']:.0f} (ATH ${h['ath_mcap_usd']:.0f})\n"
        prompt += "\n"

    if candidates:
        prompt += "# Entry candidates (decide: buy / skip). All pump.fun top-runners. SOL price: $" + f"{sol_price:.2f}\n"
        for c in candidates:
            mcap_ratio = c['mcap_usd'] / c['ath_mcap_usd'] if c['ath_mcap_usd'] else 0
            prompt += f"- ${c['symbol']} ({c['mint']}) {c['name']} — ${c['price_usd']:.6g}, 24h={c['chg_24h']:+.1f}%, 1h={c['chg_1h']:+.1f}%, liq=${c['liquidity_usd']:.0f}, vol=${c['volume_24h_usd']:.0f}, mcap=${c['mcap_usd']:.0f} (ATH ${c['ath_mcap_usd']:.0f}, currently {mcap_ratio*100:.0f}% of ATH)\n"
        prompt += "\n"
    else:
        prompt += "\n# No entry candidates right now — top-runners all failing basic gates (liq/vol/momentum).\n"

    prompt += f"""# Your call

Rules of engagement (HARD limits, not negotiable):
- Each position is 0.1 SOL. You can hold up to {MAX_POSITIONS} positions.
- No new buys if today_pnl < -{DAILY_MAX_LOSS_SOL} SOL.
- No new buys if balance_sol would drop below {RESERVE_SOL} SOL after entry.
- A position can be held up to {MAX_HOLD_HOURS} hours max (hard limit).
- A token's price can drop 90% in minutes on memecoins. There are NO safe stop-losses.
- Real signal > top-runner hype. "Trending" often means smart money already exited.
- A 24h gain of 30%+ on a small-cap usually means it's pumped already. Be skeptical of late entries.
- Volume + liquidity matter for being able to exit. <$5k liq = stuck.

Output ONLY valid JSON in this exact shape:
{{
  "exit_decisions": [
    {{"mint": "<full mint from held position, or skip if no held positions>", "action": "hold|sell_all|sell_half", "reasoning": "<1-2 sentences, honest, specific to the data>"}}
  ],
  "entry_decisions": [
    {{"mint": "<full mint from candidates, or skip>", "action": "buy|skip", "reasoning": "<1-2 sentences>"}}
  ],
  "summary": "<one sentence on overall market read and what you're doing>"
}}

Be aggressive when signals support it, defensive when they don't. No token is "definitely going up." Don't paper over losses.
"""
    return prompt, held, candidates


def get_llm_decisions(prompt):
    """Call LLM, parse response, return decision list."""
    response = call_llm(prompt)
    parsed = extract_json(response)
    if not parsed:
        return None, response, "could not parse JSON"
    if not isinstance(parsed, dict):
        return None, response, "JSON not an object"
    return parsed, response, None


# =====================================================================
# Execution
# =====================================================================

def execute_buy(state, mint, token, price_usd, sol_price):
    """Open a paper position. Returns position dict or (False, reason)."""
    if state.get("balance_sol", 0) - POSITION_SIZE_SOL < RESERVE_SOL:
        return False, f"would breach reserve ({RESERVE_SOL} SOL)"
    if state.get("balance_sol", 0) < POSITION_SIZE_SOL:
        return False, "insufficient SOL"

    sol_price_usd = sol_price
    usd_value = POSITION_SIZE_SOL * sol_price_usd
    token_amount = usd_value / price_usd if price_usd > 0 else 0
    if token_amount <= 0:
        return False, "could not size position"

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
            "volume_24h_usd": token.get("volume_24h_usd"),
            "price_change_24h": token.get("price_change_h24"),
            "price_change_1h": token.get("price_change_h1"),
            "market_cap_usd": token.get("market_cap_usd"),
            "ath_market_usd": token.get("ath_market_cap_usd"),
        },
        "llm_entry": True,  # marker that LLM approved
    }
    state["positions"][mint] = position
    state["balance_sol"] = round(state["balance_sol"] - POSITION_SIZE_SOL, 6)
    return position, None


def execute_sell(state, mint, price_usd, fraction, reason):
    """Sell fraction of position. Returns trade dict."""
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
# Main loop
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


def main():
    log("=== Memecoin bot tick (v3 LLM) ===")
    state = load_state()
    now = now_utc()

    # 1. Fetch prices
    sol_price = fetch_sol_price_usd()
    if sol_price is None:
        log("ERROR: couldn't fetch SOL price")
        sys.exit(1)
    state["last_sol_price_usd"] = sol_price
    log(f"SOL: ${sol_price:.2f}")

    # 2. Fetch watchlist
    top_runners = fetch_pumpfun_top_runners(limit=30)
    mints = [t["mint"] for t in top_runners if t.get("mint")]
    dex_data = fetch_dexscreener_for_mints(mints)
    watchlist_state = build_watchlist_state(sol_price, top_runners, dex_data)
    WATCHLIST_PATH.write_text(json.dumps(watchlist_state, indent=2, ensure_ascii=False))

    # 3. Apply hard max-hold (LLM can't hold forever)
    for mint, pos in list(state.get("positions", {}).items()):
        if not pos.get("entry_time"):
            continue
        held_hours = (now - parse_iso(pos["entry_time"])).total_seconds() / 3600
        if held_hours >= MAX_HOLD_HOURS:
            token = next((t for t in watchlist_state["tokens"] if t["mint"] == mint), None)
            if token and _to_float(token.get("price_usd")) > 0:
                trade = execute_sell(state, mint, _to_float(token["price_usd"]), 1.0, f"max-hold {MAX_HOLD_HOURS}h reached")
                if trade:
                    log(f"FORCED EXIT: ${trade['symbol']} after {MAX_HOLD_HOURS}h — PnL {trade['pnl_pct']:+.1f}%")
                    append_decision({
                        "action": "sell",
                        "details": f"[max-hold] ${trade['symbol']} closed at ${trade['exit_price_usd']:.6g} | P&L: {trade['pnl_pct']:+.1f}%",
                        "reason": f"Hard cap of {MAX_HOLD_HOURS} hours reached",
                    })

    # 4. Compute portfolio + today's PnL
    portfolio = compute_portfolio_value(state, sol_price, dex_data)
    today_pnl = compute_today_realized_pnl(state)
    log(f"Portfolio: ${portfolio['total_value_usd']:.2f} | Today realized: {today_pnl:+.4f} SOL")

    # 5. Check daily loss cap
    daily_loss_breached = today_pnl < -DAILY_MAX_LOSS_SOL

    # 6. Build LLM prompt
    prompt, held, candidates = build_decision_prompt(
        state, sol_price, watchlist_state, portfolio, today_pnl
    )
    if not held and not candidates and not ALWAYS_LLM_TICK:
        log("Nothing to do — no positions, no candidates (ALWAYS_LLM_TICK=False)")
        append_decision({
            "action": "observe",
            "details": f"No positions, no candidates passed basic gates",
            "reason": "no action",
        })
        state["portfolio_value_usd"] = portfolio["total_value_usd"]
        state["last_updated"] = iso_now()
        state["recent_decisions"] = load_recent_decisions(max_n=20)
        save_state(state)
        git_commit_and_push()
        return

    # Throttle LLM calls when idle: only call every LLM_BRIEF_INTERVAL_MIN minutes
    # (still scan tokens every tick, just don't burn LLM tokens)
    if not held and not candidates and ALWAYS_LLM_TICK:
        last_brief = state.get("last_llm_brief_at")
        if last_brief:
            try:
                last_dt = parse_iso(last_brief)
                if last_dt and (now - last_dt).total_seconds() < LLM_BRIEF_INTERVAL_MIN * 60:
                    log(f"Idle + last LLM brief {(now-last_dt).total_seconds():.0f}s ago < {LLM_BRIEF_INTERVAL_MIN*60}s — skipping LLM, scanning only")
                    state["portfolio_value_usd"] = portfolio["total_value_usd"]
                    state["last_updated"] = iso_now()
                    state["recent_decisions"] = load_recent_decisions(max_n=20)
                    save_state(state)
                    git_commit_and_push()
                    return
            except Exception:
                pass
        log("No positions, no candidates — asking LLM for market read")
        # Fall through to LLM call with empty lists — it will give us a market brief
        state["last_llm_brief_at"] = iso_now()

    # 7. Get LLM decision
    log(f"Asking LLM (held={len(held)}, candidates={len(candidates)})...")
    try:
        decisions, raw_response, parse_err = get_llm_decisions(prompt)
    except Exception as e:
        log(f"ERROR: LLM call failed: {e}")
        decisions, raw_response, parse_err = None, str(e), "llm call failed"

    log_full_decision(prompt, raw_response, "tick", f"held={len(held)} candidates={len(candidates)}")

    if not decisions:
        log(f"WARN: {parse_err} — holding all positions, no entries")
        log(f"Raw response (first 500): {raw_response[:500]}")
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

    # 8. Execute exit decisions
    exits_made = 0
    for dec in decisions.get("exit_decisions", []) or []:
        if not isinstance(dec, dict):
            continue
        target_mint_prefix = dec.get("mint", "")
        action = dec.get("action", "").lower()
        reasoning = dec.get("reasoning", "")
        # Find the held position whose mint starts with the prefix
        target_mint = None
        for full_mint in state.get("positions", {}):
            if full_mint.startswith(target_mint_prefix.replace("…", "")):
                target_mint = full_mint
                break
        if not target_mint:
            continue
        token = next((t for t in watchlist_state["tokens"] if t["mint"] == target_mint), None)
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

    # 9. Execute entry decisions
    if daily_loss_breached:
        log(f"Daily loss cap reached ({today_pnl:+.4f} < -{DAILY_MAX_LOSS_SOL} SOL) — skipping entries")
        append_decision({
            "action": "observe",
            "details": f"Daily loss cap hit ({today_pnl:+.4f} SOL). No new entries today.",
            "reason": "safety guardrail",
        })
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
                full = watchlist_state["tokens"]
                for tok in full:
                    if tok["mint"].startswith(target_mint_prefix.replace("…", "")):
                        target_mint = tok["mint"]
                        break
                if target_mint:
                    break
            if not target_mint or target_mint in state.get("positions", {}):
                continue
            if len(state.get("positions", {})) >= MAX_POSITIONS:
                break
            token = next((t for t in watchlist_state["tokens"] if t["mint"] == target_mint), None)
            if not token or _to_float(token.get("price_usd")) <= 0:
                continue
            pos, err = execute_buy(state, target_mint, token, _to_float(token["price_usd"]), sol_price)
            if pos:
                log(f"LLM BUY ${pos['symbol']}: ${pos['amount']:.4f} tokens @ ${pos['entry_price_usd']:.6g} — {reasoning[:80]}")
                append_decision({
                    "action": "buy",
                    "details": f"[LLM] ${pos['symbol']} at ${pos['entry_price_usd']:.6g}, spent {POSITION_SIZE_SOL} SOL",
                    "reason": reasoning,
                })
            elif err:
                log(f"Buy blocked: {err}")

    # 10. If no actions, log observation with the LLM summary
    if exits_made == 0 and len(state.get("positions", {})) == len(held):
        summary = decisions.get("summary", "no summary")
        append_decision({
            "action": "observe",
            "details": f"LLM tick: {exits_made} exits, no entries. {len(state.get('positions', {}))} positions held",
            "reason": summary,
        })

    # 11. Update state
    state["portfolio_value_usd"] = compute_portfolio_value(state, sol_price, dex_data)["total_value_usd"]
    state["last_updated"] = iso_now()
    state["recent_decisions"] = load_recent_decisions(max_n=20)
    save_state(state)
    log(f"State saved: {len(state.get('positions', {}))} positions, {len(state.get('trades', []))} trades")

    # 12. Push
    git_commit_and_push()
    log("=== Done ===")


if __name__ == "__main__":
    main()