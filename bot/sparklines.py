"""
Sparkline storage for memecoin trading bot.
Subscribes to pumpportal.fun WebSocket, records trade events per mint,
stores last 30 min of bucketed prices to wiki/trading/sparklines.json.
"""
import json
import os
import sys
import time
import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# WebSocket is optional — install websockets if available
try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False
import urllib.request
from urllib.error import URLError

SPARKLINE_PATH = Path("/opt/data/hermes_work/wiki/trading/sparklines.json")
WS_URL = "wss://pumpportal.fun/api/data"
BUCKET_SECONDS = 30  # bucket size for sparkline aggregation
HISTORY_MINUTES = 30  # how long to keep
TICK_SECONDS = 5      # write interval (debounce)
MAX_MINTS = 50        # cap concurrent subscriptions


def load_sparklines():
    if not SPARKLINE_PATH.exists():
        return {}
    try:
        return json.loads(SPARKLINE_PATH.read_text())
    except Exception:
        return {}


def save_sparklines(data):
    SPARKLINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPARKLINE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def bucket_for_timestamp(ts):
    """Round timestamp to nearest BUCKET_SECONDS."""
    return (ts // BUCKET_SECONDS) * BUCKET_SECONDS


def trim_old_buckets(mint_data, now_ts):
    """Drop buckets older than HISTORY_MINUTES."""
    cutoff = now_ts - (HISTORY_MINUTES * 60)
    if not mint_data.get("ts"):
        return mint_data
    # Filter keeping only buckets >= cutoff
    keep_idx = [i for i, t in enumerate(mint_data["ts"]) if t >= cutoff]
    mint_data["ts"] = [mint_data["ts"][i] for i in keep_idx]
    mint_data["px"] = [mint_data["px"][i] for i in keep_idx]
    mint_data["vol"] = [mint_data["vol"][i] for i in keep_idx]
    return mint_data


def record_trade(sparklines, mint, price_sol, sol_amount, ts):
    """Record a single trade event. Bucket at 30s resolution."""
    if not mint or price_sol <= 0:
        return
    if mint not in sparklines:
        sparklines[mint] = {"ts": [], "px": [], "vol": []}
    bucket = bucket_for_timestamp(ts)
    data = sparklines[mint]
    # If last bucket is the same, update it (latest price wins)
    if data["ts"] and data["ts"][-1] == bucket:
        data["px"][-1] = price_sol
        data["vol"][-1] = (data["vol"][-1] if data["vol"] else 0) + sol_amount
    else:
        data["ts"].append(bucket)
        data["px"].append(price_sol)
        data["vol"].append(sol_amount)
    data = trim_old_buckets(data, ts)


async def subscribe_and_record(mints):
    """Subscribe to pumpportal.fun and record trades for given mints."""
    if not HAS_WS:
        print("[sparklines] websockets package not installed", file=sys.stderr)
        return
    if not mints:
        return
    mints = list(mints)[:MAX_MINTS]
    sparklines = load_sparklines()
    last_save = time.time()
    try:
        async with websockets.connect(WS_URL) as ws:
            # Subscribe to trade events for all mints
            sub_msg = {"method": "subscribeTokenTrade", "keys": mints}
            await ws.send(json.dumps(sub_msg))
            print(f"[sparklines] subscribed to {len(mints)} mints", file=sys.stderr)
            async for msg in ws:
                try:
                    ev = json.loads(msg)
                except Exception:
                    continue
                if ev.get("txType") != "buy":
                    # Track sells too — price action matters both ways
                    pass
                mint = ev.get("mint")
                sol_amount = float(ev.get("solAmount", 0) or 0)
                token_amount = float(ev.get("tokenAmount", 0) or 0)
                if not mint or token_amount <= 0:
                    continue
                # price_sol = amount of SOL per token
                price_sol = sol_amount / token_amount if token_amount > 0 else 0
                if price_sol <= 0:
                    continue
                ts = int(time.time())
                record_trade(sparklines, mint, price_sol, sol_amount, ts)
                # Debounced save
                if time.time() - last_save > TICK_SECONDS:
                    save_sparklines(sparklines)
                    last_save = time.time()
    except Exception as e:
        print(f"[sparklines] WS error: {e}", file=sys.stderr)


def main():
    """CLI mode: subscribe to specific mints (for ad-hoc testing)."""
    if len(sys.argv) < 2:
        print("Usage: python sparklines.py <mint1> [<mint2> ...]")
        print("Or import as module: from sparklines import subscribe_and_record")
        return
    mints = sys.argv[1:]
    asyncio.run(subscribe_and_record(mints))


if __name__ == "__main__":
    main()
