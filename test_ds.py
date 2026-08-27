#!/usr/bin/env python3
"""Test DexScreener WebSocket for live trade data."""
import asyncio
import json
import websockets

async def main():
    # Try DexScreener streaming
    url = "wss://io.dexscreener.com:443"
    # Subscription format: subscribe to specific pairs
    # Format example: {"event": "subscribe", "pair": ["solana/PAIRADDRESS"]}
    mints = [
        "55Ufpo4bpfUksyLtvwAtJPJy4djDayqg65kgKSnnpump",  # lily
    ]
    pairs = [f"solana/{m}" for m in mints]
    print(f"Trying {url} with {pairs}")
    try:
        async with websockets.connect(url, ping_interval=20) as ws:
            sub = {"event": "subscribe", "pair": pairs}
            await ws.send(json.dumps(sub))
            print("Subscribed")
            count = 0
            try:
                async with asyncio.timeout(20):
                    async for msg in ws:
                        print(f"  EV: {msg[:300]}")
                        count += 1
                        if count > 3:
                            break
            except asyncio.TimeoutError:
                print(f"Timeout, got {count}")
    except Exception as e:
        print(f"err: {e}")

asyncio.run(main())