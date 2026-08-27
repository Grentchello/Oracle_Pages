#!/usr/bin/env python3
"""
Sparkline collector for memecoin bot.

Polls pump.fun REST API every minute for all active memecoin positions
+ watchlist mints. Stores bucketed price history to
wiki/trading/sparklines.json. Dashboard reads from this for sparkline charts.

Used by bot.py to inject price history into LLM prompt.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
WORK_DIR = SCRIPT_DIR.parent
WIKI_DIR = WORK_DIR / "wiki"
STATE_PATH = WIKI_DIR / "trading" / "state.json"
WATCHLIST_PATH = WIKI_DIR / "trading" / "watchlist.json"
SPARKLINE_PATH = WIKI_DIR / "trading" / "sparklines.json"

BUCKET_SECONDS = 60       # 1-min buckets (matches bot tick cadence)
HISTORY_MINUTES = 60      # keep last hour
PUMP_FUN_URL = "https://frontend-api-v3.pump.fun/coins/{mint}"
TICK_SECONDS = 60         # poll every minute
TIMEOUT = 5
MAX_MINTS = 30            # cap to avoid rate limits


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [sparklines] {msg}", flush=True)


def load_json(path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return default if default is not None else {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_active_mints():
    """Get mints to track: held positions + watchlist."""
    state = load_json(STATE_PATH, default={}) or {}
    watchlist = load_json(WATCHLIST_PATH, default={}) or {}
    mints = set()
    for m in state.get("positions", {}):
        mints.add(m)
    for t in watchlist.get("tokens", []):
        if t.get("mint"):
            mints.add(t["mint"])
    return list(mints)[:MAX_MINTS]


def fetch_price(mint):
    """Get current price for a mint via pump.fun bonding curve. Returns price_sol or 0."""
    try:
        url = PUMP_FUN_URL.format(mint=mint)
        req = urllib.request.Request(url, headers={"User-Agent": "oracle-vault-sparklines/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read())
    except Exception as e:
        log(f"  err {mint[:12]}: {str(e)[:50]}")
        return 0
    vsr = float(data.get("virtual_sol_reserves", 0) or 0) / 1e9
    vtr = float(data.get("virtual_token_reserves", 0) or 0) / 1e6
    if vsr > 0 and vtr > 0:
        return vsr / vtr
    return 0


def bucket_for(ts):
    return (ts // BUCKET_SECONDS) * BUCKET_SECONDS


def trim_old(data):
    cutoff = int(time.time()) - (HISTORY_MINUTES * 60)
    for mint in list(data.keys()):
        d = data[mint]
        if not d.get("ts"):
            del data[mint]
            continue
        keep = [i for i, t in enumerate(d["ts"]) if t >= cutoff]
        d["ts"] = [d["ts"][i] for i in keep]
        d["px"] = [d["px"][i] for i in keep]
        if not d["ts"]:
            del data[mint]


def record(data, mint, price_sol):
    """Append price point to bucket for mint."""
    if not mint or price_sol <= 0:
        return
    if mint not in data:
        data[mint] = {"ts": [], "px": []}
    d = data[mint]
    bucket = bucket_for(int(time.time()))
    if d["ts"] and d["ts"][-1] == bucket:
        d["px"][-1] = price_sol
    else:
        d["ts"].append(bucket)
        d["px"].append(price_sol)


def main():
    log("starting sparkline collector (pump.fun polling)")
    data = load_json(SPARKLINE_PATH, default={}) or {}
    while True:
        try:
            mints = get_active_mints()
            if not mints:
                log("no mints, sleeping")
                time.sleep(TICK_SECONDS)
                continue
            log(f"polling {len(mints)} mints")
            fetched = 0
            for m in mints:
                price = fetch_price(m)
                if price > 0:
                    record(data, m, price)
                    fetched += 1
                time.sleep(0.05)  # 20 req/sec, well within pump.fun limits
            trim_old(data)
            save_json(SPARKLINE_PATH, data)
            log(f"saved {len(mints)} mints ({fetched} with prices)")
        except Exception as e:
            log(f"main loop err: {e}")
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
