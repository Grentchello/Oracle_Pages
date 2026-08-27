#!/usr/bin/env python3
"""Test pump.fun coin endpoint rate limit and response time."""
import time
import urllib.request
import json

mints = ["55Ufpo4bpfUksyLtvwAtJPJy4djDayqg65kgKSnnpump"] * 5  # test 5 seq requests
# Then test 5 more
mints += [
    "ED5JXBQ82WsZe1meueymTgT2XPhYjRfe6Yqiqspepump",
    "Byxnq9AxaJ6zEbxkvQPD5DmCC3tb2TnAfRHCV7L9pump",
    "FQjKMpNfBbiBYoRa7xp7cGwz9asBDn32cURUS8pWpump",
    "rUH3jVHCpaPWegeVAF1ebSF7tm5S7hpPCxRMyMVpump",
]

start = time.time()
results = []
for i, m in enumerate(mints):
    try:
        r = urllib.request.urlopen(f"https://frontend-api-v3.pump.fun/coins/{m}", timeout=5)
        data = json.loads(r.read())
        price = (data.get("virtual_sol_reserves", 0) / 1e9) / (data.get("virtual_token_reserves", 0) / 1e6) if data.get("virtual_token_reserves") else 0
        results.append({"mint": m[:12], "status": r.status, "ts": data.get("last_trade_timestamp"), "price_sol": price})
    except Exception as e:
        results.append({"mint": m[:12], "err": str(e)[:80]})
elapsed = time.time() - start
print(f"\nFetched {len(mints)} mints in {elapsed:.1f}s ({elapsed/len(mints):.2f}s/req)")
for r in results:
    print(f"  {r}")