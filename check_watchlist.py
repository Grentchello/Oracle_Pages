import json, urllib.request
req = urllib.request.Request("https://grentchello.github.io/Oracle_Pages/trading/watchlist.json", headers={"User-Agent":"test"})
with urllib.request.urlopen(req, timeout=15) as r:
    w = json.loads(r.read())

# Check all tokens for our 5 held positions
held_mints = [
    "ED5JXBQ82WsZ",  # LEGEND
    "Byxnq9AxaJ6z",  # Toad
    "5UzV8kS6HwNW",  # Queefcoin
    "FQjKMpNfBbiB",  # Panana
    "rUH3jVHCpaPW",  # gOOn
]

print("Looking for held tokens in watchlist:")
for prefix in held_mints:
    found = False
    for t in w.get("tokens", []):
        if t.get("mint", "").startswith(prefix):
            print(f"  {prefix}: ${t.get('symbol'):10} price_usd={t.get('price_usd')} liq={t.get('liquidity_usd')} vol={t.get('volume_h24')}")
            found = True
            break
    if not found:
        print(f"  {prefix}: NOT IN WATCHLIST")

# Also show all tokens with their prices
print(f"\nTotal tokens: {len(w.get('tokens', []))}")
print("Tokens with valid price_usd:")
n_with_price = 0
for t in w.get("tokens", []):
    if t.get("price_usd") is not None and _to_float(t.get("price_usd")) > 0:
        n_with_price += 1
print(f"  {n_with_price} / {len(w.get('tokens', []))}")

def _to_float(v, default=0.0):
    if v is None: return default
    try: return float(v)
    except: return default