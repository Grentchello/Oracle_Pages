#!/usr/bin/env python3
"""
Sparkline collector — runs as background process.

Subscribes to pumpportal.fun WS, records trades for all currently-held
memecoin positions + watchlist entries, stores bucketed history to
wiki/trading/sparklines.json.

Run: python3 sparkline_collector.py
Stops on SIGINT.
"""
import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path

import websockets
import urllib.request

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
WORK_DIR = SCRIPT_DIR.parent
WIKI_DIR = WORK_DIR / "wiki"
STATE_PATH = WIKI_DIR / "trading" / "state.json"
WATCHLIST_PATH = WIKI_DIR / "trading" / "watchlist.json"
SPARKLINE_PATH = WIKI_DIR / "trading" / "sparklines.json"

# Config
WS_URL = "wss://pumpportal.fun/api/data"
BUCKET_SECONDS = 30
HISTORY_MINUTES = 30
SAVE_INTERVAL_SECONDS = 5
RESUBSCRIBE_INTERVAL_SECONDS = 300  # refresh subscriptions every 5 min (new positions emerge)


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [sparkline-collector] {msg}", flush=True)


def load_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_active_mints():
    """Return set of mints to track: held positions + watchlist."""
    state = load_json(STATE_PATH, default={}) or {}
    watchlist = load_json(WATCHLIST_PATH, default={}) or {}
    mints = set()
    for m in state.get("positions", {}):
        mints.add(m)
    for t in watchlist.get("tokens", []):
        if t.get("mint"):
            mints.add(t["mint"])
    return mints


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
        d["vol"] = [d["vol"][i] for i in keep]
        if not d["ts"]:
            del data[mint]


def record(data, mint, price_sol, sol_amount):
    if not mint or price_sol <= 0:
        return
    if mint not in data:
        data[mint] = {"ts": [], "px": [], "vol": []}
    d = data[mint]
    bucket = bucket_for(int(time.time()))
    if d["ts"] and d["ts"][-1] == bucket:
        d["px"][-1] = price_sol
        d["vol"][-1] += sol_amount
    else:
        d["ts"].append(bucket)
        d["px"].append(price_sol)
        d["vol"].append(sol_amount)


async def run():
    log(f"Starting sparkline collector, WS URL: {WS_URL}")
    data = load_json(SPARKLINE_PATH, default={}) or {}
    last_save = 0.0
    last_resub = 0.0

    while True:
        try:
            mints = get_active_mints()
            if not mints:
                log("no active mints, sleeping")
                await asyncio.sleep(30)
                continue

            log(f"subscribing to {len(mints)} mints")
            async with websockets.connect(WS_URL, ping_interval=20) as ws:
                # Subscribe
                sub = {"method": "subscribeTokenTrade", "keys": list(mints)[:50]}
                await ws.send(json.dumps(sub))
                last_resub = time.time()

                async for msg in ws:
                    try:
                        ev = json.loads(msg)
                    except Exception:
                        continue
                    mint = ev.get("mint")
                    if not mint:
                        continue
                    sol_amount = float(ev.get("solAmount", 0) or 0)
                    token_amount = float(ev.get("tokenAmount", 0) or 0)
                    if token_amount <= 0:
                        continue
                    price_sol = sol_amount / token_amount
                    record(data, mint, price_sol, sol_amount)

                    # Debounced save
                    now = time.time()
                    if now - last_save > SAVE_INTERVAL_SECONDS:
                        trim_old(data)
                        save_json(SPARKLINE_PATH, data)
                        last_save = now

                    # Periodic resubscribe for new positions
                    if now - last_resub > RESUBSCRIBE_INTERVAL_SECONDS:
                        log("resubscribing to fresh mints")
                        # Current mints may have changed — rebuild subscription
                        mints_now = get_active_mints()
                        new_sub = {"method": "subscribeTokenTrade", "keys": list(mints_now)[:50]}
                        await ws.send(json.dumps(new_sub))
                        last_resub = now

        except Exception as e:
            log(f"WS error: {e}, reconnecting in 10s")
            await asyncio.sleep(10)


def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
