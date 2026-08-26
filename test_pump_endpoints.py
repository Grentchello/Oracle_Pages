import json, sys

def dump(label, url):
    print(f"\n=== {label} ===")
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "test"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        items = data if isinstance(data, list) else data.get("coins", data.get("items", data.get("data", [])))
        print(f"got {len(items)} items")
        for t in items[:8]:
            ts = t.get("created_timestamp", 0)
            age_min = "?" if not ts else round((1787722000000 - ts) / 60000, 1)
            mcap = t.get("market_cap_usd", 0) or t.get("usd_market_cap", 0)
            print(f"  {t.get('symbol','?'):12} mcap=${mcap:>12,.0f} complete={t.get('complete')} age={age_min}min vol={t.get('volatility_score','?')}")
    except Exception as e:
        print(f"error: {e}")

dump("newest", "https://frontend-api-v3.pump.fun/coins/recent?limit=5&offset=0")
dump("king-of-hill", "https://frontend-api-v3.pump.fun/coins/king-of-the-hill?limit=5&offset=0")
dump("graduating", "https://frontend-api-v3.pump.fun/coins/graduating?limit=5&offset=0")