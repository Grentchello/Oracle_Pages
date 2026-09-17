import json
import re
import subprocess
from datetime import datetime, timezone
from collections import defaultdict

with open("/opt/data/hermes_work/wiki/trading/state.json") as f:
    state = json.load(f)

trades = state["trades"]
balance = state["balance_sol"]
positions = state["positions"]

print(f"Current balance (SOL): {balance:.6f}")
print(f"Open positions: {len(positions)}")
print(f"Total trades logged: {len(trades)}")

result = subprocess.run(
    ["grep", "-n", r"\[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} UTC\] eval",
     "/opt/data/hermes_work/wiki/log.md"],
    capture_output=True, text=True
)
last_eval_ts = None
last_eval_trade_count = 0
for line in result.stdout.strip().split("\n")[::-1]:
    if not line:
        continue
    m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC\] eval.*?trades=(\d+)", line)
    if m:
        last_eval_ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        last_eval_trade_count = int(m.group(2))
        print(f"Last eval: {last_eval_ts.isoformat()}, trades count at that time: {last_eval_trade_count}")
        break

if last_eval_ts is None:
    print("No prior eval found in log.md - using full history")
    last_eval_ts = datetime(2000, 1, 1, tzinfo=timezone.utc)

new_trades = [t for t in trades if datetime.fromisoformat(t["exit_time"]) > last_eval_ts]
print(f"Trades since last eval: {len(new_trades)}")

def stats(tlist, label):
    if not tlist:
        print(f"\n=== {label}: no trades ===")
        return 0
    wins = sum(1 for t in tlist if t.get("pnl_sol", 0) > 0)
    losses = sum(1 for t in tlist if t.get("pnl_sol", 0) <= 0)
    total_pnl = sum(t.get("pnl_sol", 0) for t in tlist)
    total_sold = sum(t.get("exit_sol_received", 0) for t in tlist)
    win_rate = wins / len(tlist) * 100
    partials = sum(1 for t in tlist if t.get("partial"))
    print(f"\n=== {label} ({len(tlist)} trades) ===")
    print(f"  Wins: {wins}  Losses: {losses}  Win rate: {win_rate:.1f}%")
    print(f"  Total PnL (SOL): {total_pnl:+.6f}")
    print(f"  Total SOL received from exits: {total_sold:.6f}")
    print(f"  Partials (sell_half): {partials}")
    tp_wins = 0
    override_wins = 0
    rapid_losses = 0
    hard_cap_losses = 0
    other = 0
    for t in tlist:
        reason = (t.get("exit_reason") or "").lower()
        pnl = t.get("pnl_sol", 0)
        held_min = (datetime.fromisoformat(t["exit_time"]) - datetime.fromisoformat(t["entry_time"])).total_seconds() / 60
        if pnl > 0 and "sell_half" in reason:
            tp_wins += 1
        elif pnl > 0 and "sell_all" in reason:
            override_wins += 1
        elif pnl <= 0 and held_min < 30:
            rapid_losses += 1
        elif pnl <= 0 and "-50%" in reason:
            hard_cap_losses += 1
        else:
            other += 1
    print(f"  TP partial wins (sell_half + profit): {tp_wins}")
    print(f"  Override sell_all wins: {override_wins}")
    print(f"  Rapid losses (<30min held): {rapid_losses}")
    print(f"  Hard-cap losses (-50% rule): {hard_cap_losses}")
    print(f"  Other (slow bleed, narrative exit): {other}")
    return total_pnl

pnl_new = stats(new_trades, "SINCE LAST EVAL")
stats(trades, "ALL TIME")

total_sol_in = sum(t.get("entry_sol_for_chunk", 0) for t in trades)
total_sol_out = sum(t.get("exit_sol_received", 0) for t in trades)
print(f"\nTotal SOL deployed via entry chunks: {total_sol_in:.6f}")
print(f"Total SOL returned via exits: {total_sol_out:.6f}")
print(f"Net (entries - exits): {total_sol_in - total_sol_out:+.6f}  [>0 means capital still deployed in open positions or lost]")

print("\n--- Slippage reality check (last 20 trades) ---")
for t in trades[-20:]:
    pnl = t["pnl_sol"]
    buy = t["entry_sol_for_chunk"]
    sold = t["exit_sol_received"]
    pct_pnl = (pnl / buy * 100) if buy > 0 else 0
    realized_pct = ((sold - buy) / buy * 100) if buy > 0 else 0
    print(f"  {t['symbol']:12s} buy={buy:.4f} sold={sold:.4f} reported_pnl={pnl:+.6f} ({pct_pnl:+.1f}%)  realized={realized_pct:+.1f}%")
