#!/usr/bin/env python3
"""Test if Solana RPC works."""
import json, urllib.request, sys

RPCS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-mainnet.g.alchemy.com/v2/demo",
]

# Test wallet we know exists
test_addr = "vines1vzrYbzLMRH58vQz1J8G7Kb6ZcY8ZJ8ZJ8ZJ8ZJ8"  # random - should not exist
known_addr = "JUP6LkbZbiS2gQt4xfGZGE2xK8KJp8ZJ8ZJ8ZJ8ZJ8"  # JUP token

for rpc in RPCS:
    print(f"Testing {rpc}")
    try:
        req = urllib.request.Request(rpc, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
            "params": [known_addr]
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            print(f"  Response: {json.dumps(d)[:200]}")
    except Exception as e:
        print(f"  Error: {e}")
    print()
