import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

state = json.loads(Path("/opt/data/hermes_work/bot/base_memecoin/data/state.json").read_text())
trades = state["trades"]

STARTING = state.get("starting_balance_eth", 0.10)
print(f"Starting balance: {STARTING} ETH")

by_day = {}
for t in trades:
    d = t["exit_time"][:10]
    by_day.setdefault(d, []).append(t)

running = STARTING
for d in sorted(by_day.keys()):
    ts = by_day[d]
    pnl = sum(t["pnl_eth"] for t in ts)
    n = len(ts)
    running += pnl
    print(f"{d}: {n:3d} trades, pnl={pnl:+.6f}, running_balance={running:.6f}")
print(f"\nFinal state balance: {state.get('balance_eth')} ETH")
print(f"Total trades: {len(trades)}")

print(f"\nv3_reset: {state.get('v3_reset')}")
print(f"created: {state.get('created')}")
print(f"total_pnl_eth: {state.get('total_pnl_eth')}")

ghost = [t for t in trades if t.get("ghost_exit")]
print(f"\nghost_exit trades: {len(ghost)}")

positions = state.get("positions", {})
print(f"\nOpen positions: {len(positions)}")
for k, v in list(positions.items())[:5]:
    print(f"  {k}: {v.get('symbol')} entry={v.get('entry_time')} pnl_pct={v.get('pnl_pct', '?')}")

# 7d trend
last7 = datetime.now(timezone.utc) - timedelta(days=7)
t7 = [t for t in trades if datetime.fromisoformat(t["exit_time"].replace("Z","+00:00")) > last7]
print(f"\nLast 7d: {len(t7)} trades, pnl={sum(t['pnl_eth'] for t in t7):+.6f}")
