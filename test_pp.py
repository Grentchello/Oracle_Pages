#!/usr/bin/env python3
"""Quick test of pumpportal WS - inspect raw events."""
import asyncio
import json
import urllib.request
import websockets

async def main():
    try:
        data = json.loads(urllib.request.urlopen("https://frontend-api-v3.pump.fun/coins?limit=15&offset=0&sort=last_trade_timestamp&order=DESC&includeNsfw=false", timeout=10).read())
        mints = [t.get("mint") for t in data if t.get("mint")][:15]
        print(f"Pulled {len(mints)} recent mints")
    except Exception as e:
        print(f"err: {e}")
        mints = []

    print(f"Connecting to wss://pumpportal.fun/api/data ...")
    async with websockets.connect("wss://pumpportal.fun/api/data", ping_interval=20) as ws:
        sub = {"method": "subscribeTokenTrade", "keys": mints}
        await ws.send(json.dumps(sub))
        print(f"Subscribed to {len(mints)} mints")
        print("Listening for 30s ...")
        count = 0
        try:
            async with asyncio.timeout(30):
                async for msg in ws:
                    print(f"  RAW: {msg[:400]}")
                    count += 1
                    if count > 3:
                        break
        except asyncio.TimeoutError:
            print(f"Timeout after 30s. Got {count} events.")

asyncio.run(main())