import json
from collections import Counter

with open("/opt/data/hermes_work/wiki/trading/state.json") as f:
    state = json.load(f)

trades = state["trades"]
print(f"Total trades: {len(trades)}")
print(f"Balance now: {state['balance_sol']} SOL")

wins = [t for t in trades if t["pnl_sol"] > 0.0001]
losses = [t for t in trades if t["pnl_sol"] < -0.0001]
zero = [t for t in trades if abs(t["pnl_sol"]) <= 0.0001]

print(f"Wins: {len(wins)} | Losses: {len(losses)} | ~Zero: {len(zero)}")
total_pnl = sum(t["pnl_sol"] for t in trades)
print(f"Net PnL: {total_pnl:.6f} SOL")
print(f"Gross wins: {sum(t['pnl_sol'] for t in wins):.6f} SOL")
print(f"Gross losses: {sum(t['pnl_sol'] for t in losses):.6f} SOL")
nonzero = len(wins) + len(losses)
print(f"Win rate (nonzero): {len(wins)/nonzero*100:.1f}%")

implied_start = state["balance_sol"] - total_pnl
print(f"Implied starting balance: {implied_start:.4f} SOL")

cats = Counter()
for t in trades:
    r = t.get("exit_reason", "")
    pnl = t["pnl_sol"]
    partial = t.get("partial", False)
    if "ghost" in r.lower() or "rug" in r.lower() or "pool=0" in r.lower():
        cats["ghost/rug (-100%)"] += 1
    elif "-50%" in r or "hard cap" in r.lower():
        cats["hard cap -50%"] += 1
    elif pnl > 0.0001 and partial:
        cats["TP-half win"] += 1
    elif pnl > 0.0001 and not partial:
        cats["TP-full win"] += 1
    elif pnl < -0.0001 and not partial:
        cats["full loss (cut early)"] += 1
    elif pnl < -0.0001 and partial:
        cats["half loss (cut early)"] += 1
    else:
        cats["flat/zero"] += 1

print("\nExit categories:")
for k, v in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

recent = sorted(trades, key=lambda x: x.get("exit_time",""), reverse=True)[:5]
print("\nMost recent 5 trades:")
for t in recent:
    print(f"  {t['symbol']:12s} {t['pnl_pct']:+7.1f}%  {t['pnl_sol']:+.6f} SOL  {t['exit_time']}")