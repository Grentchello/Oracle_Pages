#!/usr/bin/env python3
"""Quick test of pumpportal WS - 60 second trace."""
import asyncio
import json
import websockets

async def main():
    mints = [
        "55Ufpo4bpfUksyLtvwAtJPJy4djDayqg65kgKSnnpump",  # lily
        "ED5JXBQ82WsZe1meueymTgT2XPhYjRfe6Yqiqspepump",  # LEGEND
    ]
    print(f"Connecting to wss://pumpportal.fun/api/data ...")
    async with websockets.connect("wss://pumpportal.fun/api/data", ping_interval=20) as ws:
        sub = {"method": "subscribeTokenTrade", "keys": mints}
        await ws.send(json.dumps(sub))
        print(f"Subscribed: {sub}")
        print("Listening for 30s ...")
        count = 0
        try:
            async with asyncio.timeout(30):
                async for msg in ws:
                    ev = json.loads(msg)
                    print(f"  TRADE: {ev.get('mint', '?')[:12]}... solAmount={ev.get('solAmount')}")
                    count += 1
                    if count > 5:
                        print("Got 5+ events, stopping")
                        break
        except asyncio.TimeoutError:
            print(f"Timeout after 30s. Got {count} events.")
        except Exception as e:
            print(f"Stopped: {e}, got {count} events")

asyncio.run(main())