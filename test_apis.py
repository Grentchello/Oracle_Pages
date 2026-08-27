#!/usr/bin/env python3
"""Test public REST endpoints for live trade data."""
import json
import urllib.request

def test_pumpapi():
    """pumpapi.io may have a public stream."""
    try:
        r = urllib.request.urlopen("https://pumpapi.io/", timeout=5)
        print(f"pumpapi.io: {r.status}")
    except Exception as e:
        print(f"pumpapi.io err: {e}")

def test_birdeye():
    """birdeye public price API."""
    try:
        r = urllib.request.urlopen("https://public-api.birdeye.so/defi/price?address=So11111111111111111111111111111111111111112", timeout=5)
        print(f"birdeye: {r.status} {r.read()[:100]}")
    except Exception as e:
        print(f"birdeye err: {e}")

def test_dexscreener():
    """DexScreener token profile — has price data."""
    mints = [
        "55Ufpo4bpfUksyLtvwAtJPJy4djDayqg65kgKSnnpump",
    ]
    for m in mints:
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{m}"
            r = urllib.request.urlopen(url, timeout=5)
            data = json.loads(r.read())
            pairs = data.get("pairs", [])
            if pairs:
                p = pairs[0]
                print(f"DexScreener {m[:12]}: ${p.get('priceUsd')} liq=${(p.get('liquidity') or {}).get('usd')} txns5m={(p.get('txns') or {}).get('m5', {})}")
        except Exception as e:
            print(f"DexScreener err: {e}")

def test_pump_recent_trades():
    """pump.fun coin endpoint may have recent trades."""
    m = "55Ufpo4bpfUksyLtvwAtJPJy4djDayqg65kgKSnnpump"
    try:
        url = f"https://frontend-api-v3.pump.fun/coins/{m}"
        r = urllib.request.urlopen(url, timeout=5)
        data = json.loads(r.read())
        print(f"pump.fun coin {m[:12]}: ts={data.get('last_trade_timestamp')} price via vsr/vtr")
        vsr = data.get('virtual_sol_reserves', 0) / 1e9
        vtr = data.get('virtual_token_reserves', 0) / 1e6
        if vsr > 0 and vtr > 0:
            print(f"  price = {vsr/vtr:.10f} SOL")
    except Exception as e:
        print(f"pump.fun err: {e}")

test_pumpapi()
test_birdeye()
test_dexscreener()
test_pump_recent_trades()