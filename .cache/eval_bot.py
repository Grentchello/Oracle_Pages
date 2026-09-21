import json
from collections import defaultdict
from datetime import datetime, timezone
import re

state = json.load(open('/opt/data/hermes_work/wiki/trading/state.json'))
trades = state['trades']
balance = state['balance_sol']

print(f"Current balance: {balance} SOL")
print(f"Total trades: {len(trades)}")
print(f"Positions open: {len(state['positions'])}")

# Realized PnL
total_pnl = sum(t['pnl_sol'] for t in trades)
total_wins = sum(1 for t in trades if t['pnl_sol'] > 0)
total_losses = sum(1 for t in trades if t['pnl_sol'] < 0)
total_win_sol = sum(t['pnl_sol'] for t in trades if t['pnl_sol'] > 0)
total_loss_sol = sum(t['pnl_sol'] for t in trades if t['pnl_sol'] < 0)

print(f"\nNet PnL (realized): {total_pnl:.6f} SOL")
print(f"Wins: {total_wins} | Losses: {total_losses}")
print(f"Win rate: {100*total_wins/len(trades):.1f}%")
print(f"Total win SOL: {total_win_sol:.4f}")
print(f"Total loss SOL: {total_loss_sol:.4f}")

def categorize(t):
    r = t['exit_reason'].lower()
    if ('hard cap' in r or '-50%' in r or 'breached' in r) and t['pnl_sol'] < 0:
        return 'hard_cap_loss'
    if 'sell_half' in r:
        return 'tp_partial'
    if 'sell_all' in r and t['pnl_sol'] > 0:
        return 'tp_full'
    if 'sell_all' in r and t['pnl_sol'] < 0:
        return 'early_loss'
    return 'neutral_cut'

cats = defaultdict(lambda: {'count': 0, 'pnl': 0.0, 'wins': 0, 'losses': 0})
for t in trades:
    c = categorize(t)
    cats[c]['count'] += 1
    cats[c]['pnl'] += t['pnl_sol']
    if t['pnl_sol'] > 0: cats[c]['wins'] += 1
    else: cats[c]['losses'] += 1

print("\n=== Categorized Exits ===")
for cat, data in sorted(cats.items(), key=lambda x: -x[1]['count']):
    print(f"{cat:18} n={data['count']:4}  wins={data['wins']:3}  losses={data['losses']:3}  pnl={data['pnl']:+.4f}")

times = [t['entry_time'] for t in trades]
latest = max(times)
print(f"\nFirst trade: {min(times)}")
print(f"Last entry:  {latest}")

# Parse log.md for last eval
log = open('/opt/data/hermes_work/wiki/log.md').read()
matches = re.findall(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC\] eval', log, re.MULTILINE)
last_eval_time = None
if matches:
    last_eval_time = datetime.strptime(matches[-1], '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
    print(f"\nLast eval timestamp: {last_eval_time}")

recent_trades = []
for t in trades:
    et = datetime.fromisoformat(t['entry_time'])
    if last_eval_time and et >= last_eval_time:
        recent_trades.append(t)

print(f"\n=== Trades since last eval ===")
print(f"Count: {len(recent_trades)}")
if recent_trades:
    r_pnl = sum(t['pnl_sol'] for t in recent_trades)
    r_wins = sum(1 for t in recent_trades if t['pnl_sol'] > 0)
    r_losses = sum(1 for t in recent_trades if t['pnl_sol'] < 0)
    print(f"Net PnL: {r_pnl:+.4f} SOL")
    print(f"Win/Loss: {r_wins}/{r_losses}")

# Try a 2-hour window
two_hours_ago = datetime.now(timezone.utc) - __import__('datetime').timedelta(hours=2)
# Use latest trade time as the "now"
latest_dt = datetime.fromisoformat(latest)
window_start = latest_dt - __import__('datetime').timedelta(hours=2)
window_trades = [t for t in trades if datetime.fromisoformat(t['entry_time']) >= window_start]
w_pnl = sum(t['pnl_sol'] for t in window_trades)
w_wins = sum(1 for t in window_trades if t['pnl_sol'] > 0)
w_losses = sum(1 for t in window_trades if t['pnl_sol'] < 0)
print(f"\n=== Last 2h window from latest entry ===")
print(f"Window: {window_start} -> {latest_dt}")
print(f"Count: {len(window_trades)}, Net PnL: {w_pnl:+.4f} SOL, W/L: {w_wins}/{w_losses}")
