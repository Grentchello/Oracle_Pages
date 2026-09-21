import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter

state_path = Path("/opt/data/hermes_work/bot/base_memecoin/data/state.json")
state = json.loads(state_path.read_text())
trades = state["trades"]

now = datetime.now(timezone.utc)
last24 = now - timedelta(hours=24)
t24 = [t for t in trades if datetime.fromisoformat(t["exit_time"].replace("Z","+00:00")) > last24]

print(f"=== Last 24h analysis (n={len(t24)}) ===")
print(f"Net PnL: {sum(t['pnl_eth'] for t in t24):+.6f} ETH")
wins = [t for t in t24 if t['pnl_eth']>0]
losses = [t for t in t24 if t['pnl_eth']<0]
print(f"Win rate: {len(wins)/len(t24)*100:.1f}%")
if wins: print(f"Avg win:  {sum(t['pnl_eth'] for t in wins)/len(wins):+.6f}")
if losses: print(f"Avg loss: {sum(t['pnl_eth'] for t in losses)/len(losses):+.6f}")

reasons = Counter()
for t in t24:
    r = t.get("exit_reason", "")
    if "max-hold" in r:
        reasons["max-hold"] += 1
    elif "hard-stop" in r:
        reasons["hard-stop"] += 1
    elif "TP" in r:
        reasons["TP"] += 1
    elif "ghost" in r:
        reasons["ghost_exit"] += 1
    else:
        reasons["other:" + r[:30]] += 1
print(f"\nExit reasons (last 24h): {dict(reasons)}")

by_reason_pnl = {}
for t in t24:
    key = "max-hold" if "max-hold" in t.get("exit_reason","") else ("hard-stop" if "hard-stop" in t.get("exit_reason","") else ("TP" if "TP" in t.get("exit_reason","") else "other"))
    by_reason_pnl.setdefault(key, []).append(t["pnl_eth"])
print(f"\nPnL by reason (last 24h):")
for k, vs in by_reason_pnl.items():
    print(f"  {k}: count={len(vs)}, sum={sum(vs):+.6f}, avg={sum(vs)/len(vs):+.6f}")

pcts = [t["pnl_pct"] for t in t24]
big_wins = sum(1 for p in pcts if p >= 50)
med_wins = sum(1 for p in pcts if 20 <= p < 50)
small_wins = sum(1 for p in pcts if 0 < p < 20)
flat = sum(1 for p in pcts if p == 0)
small_losses = sum(1 for p in pcts if -20 < p < 0)
med_losses = sum(1 for p in pcts if -50 < p <= -20)
big_losses = sum(1 for p in pcts if p <= -50)
print(f"\npnl_pct distribution last 24h:")
print(f"  >=+50% (TP3): {big_wins}")
print(f"  +20..+50% (TP2): {med_wins}")
print(f"  0..+20% (TP1): {small_wins}")
print(f"  0% (flat): {flat}")
print(f"  -20..0%: {small_losses}")
print(f"  -50..-20%: {med_losses}")
print(f"  <=-50% (hard stop): {big_losses}")

holds = [t["hold_seconds"]/60 for t in t24 if "hold_seconds" in t]
if holds:
    print(f"\nHold time (min): avg={sum(holds)/len(holds):.1f}, max={max(holds):.1f}, min={min(holds):.1f}")
    near_max = sum(1 for h in holds if h >= 14.5)
    print(f"  Held >=14.5min (near max-hold): {near_max}/{len(holds)} = {near_max/len(holds)*100:.1f}%")

slow_bleeds = [t for t in t24 if "max-hold" in t.get("exit_reason","") and t["pnl_eth"] < 0]
print(f"\nMax-hold positions closed at a loss: {len(slow_bleeds)}/{len(by_reason_pnl.get('max-hold', []))}")
if slow_bleeds:
    avg_loss = sum(t["pnl_eth"] for t in slow_bleeds)/len(slow_bleeds)
    print(f"  Average loss on max-hold exits: {avg_loss:+.6f} ETH")
    print(f"  Total loss on max-hold exits: {sum(t['pnl_eth'] for t in slow_bleeds):+.6f} ETH")

last2 = now - timedelta(hours=2)
t2 = [t for t in trades if datetime.fromisoformat(t["exit_time"].replace("Z","+00:00")) > last2]
print(f"\n=== Last 2h (n={len(t2)}) ===")
print(f"Net PnL: {sum(t['pnl_eth'] for t in t2):+.6f} ETH")
print(f"Win rate: {sum(1 for t in t2 if t['pnl_eth']>0)/max(1,len(t2))*100:.1f}%")
max_hold_2h = [t for t in t2 if "max-hold" in t.get("exit_reason","")]
print(f"Max-hold exits in 2h: {len(max_hold_2h)}")
if max_hold_2h:
    print(f"  PnL on max-hold exits: {sum(t['pnl_eth'] for t in max_hold_2h):+.6f}")
    bl = [t for t in max_hold_2h if t['pnl_eth']<0]
    bw = [t for t in max_hold_2h if t['pnl_eth']>0]
    print(f"  wins: {len(bw)}, losses: {len(bl)}")
    if bl: print(f"  avg loss on max-hold: {sum(t['pnl_eth'] for t in bl)/len(bl):+.6f}")
    if bw: print(f"  avg win on max-hold:  {sum(t['pnl_eth'] for t in bw)/len(bw):+.6f}")
