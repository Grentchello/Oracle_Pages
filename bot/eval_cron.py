import json
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

with open('/opt/data/hermes_work/wiki/trading/state.json') as f:
    state = json.load(f)

trades = state['trades']
balance = state['balance_sol']
total_pnl = sum(t['pnl_sol'] for t in trades)
n = len(trades)

wins = [t for t in trades if t['pnl_sol'] > 0]
losses = [t for t in trades if t['pnl_sol'] <= 0]
win_rate = len(wins) / n * 100 if n else 0

def categorize(t):
    r = t.get('exit_reason', '').lower()
    pnl = t['pnl_sol']
    pct = t['pnl_pct']
    if pnl > 0 and 'partial' in r:
        return 'TP partial profit'
    if pnl > 0:
        return 'TP full profit'
    if 'hard cap' in r or 'breached' in r or 'past the -50' in r or '-50% hard cap' in r:
        return 'Hard cap loss (-50%)'
    if pct <= -60:
        return 'Rapid loss (<= -60%)'
    if pnl < 0:
        return 'Other loss'
    return 'Break-even'

cats = Counter(categorize(t) for t in trades)
print(f"Total trades: {n}")
print(f"Current balance: {balance:.6f} SOL")
print(f"Cumulative PnL: {total_pnl:+.6f} SOL")
print(f"Win rate: {win_rate:.2f}% ({len(wins)}W / {len(losses)}L)")
print("")
print("Breakdown:")
for k, v in sorted(cats.items(), key=lambda x: -x[1]):
    sub = [t for t in trades if categorize(t) == k]
    sub_pnl = sum(t['pnl_sol'] for t in sub)
    sub_w = sum(1 for t in sub if t['pnl_sol'] > 0)
    sub_l = sum(1 for t in sub if t['pnl_sol'] <= 0)
    print(f"  {k}: {v} trades ({sub_w}W/{sub_l}L), PnL {sub_pnl:+.6f} SOL")

times = sorted(t['exit_time'] for t in trades)
print(f"\nFirst trade: {times[0]}")
print(f"Last trade:  {times[-1]}")

now = datetime(2026, 9, 15, 1, 42, tzinfo=timezone.utc)
last24h = [t for t in trades if datetime.fromisoformat(t['exit_time']) > now - timedelta(hours=24)]
last2h = [t for t in trades if datetime.fromisoformat(t['exit_time']) > now - timedelta(hours=2)]
last7d = [t for t in trades if datetime.fromisoformat(t['exit_time']) > now - timedelta(days=7)]
print(f"\nLast 2h:  {len(last2h)} trades, PnL {sum(t['pnl_sol'] for t in last2h):+.6f} SOL")
print(f"Last 24h: {len(last24h)} trades, PnL {sum(t['pnl_sol'] for t in last24h):+.6f} SOL")
print(f"Last 7d:  {len(last7d)} trades, PnL {sum(t['pnl_sol'] for t in last7d):+.6f} SOL")

token_pnl = defaultdict(float)
token_trades = defaultdict(int)
for t in trades:
    token_pnl[t['mint']] += t['pnl_sol']
    token_trades[t['mint']] += 1
sorted_tokens = sorted(token_pnl.items(), key=lambda x: x[1])
print(f"\nWorst tokens (cumulative):")
for mint, pnl in sorted_tokens[:5]:
    print(f"  {pnl:+.6f}  trades={token_trades[mint]}  {mint[:20]}...")
print(f"\nBest tokens (cumulative):")
for mint, pnl in sorted_tokens[-5:]:
    print(f"  {pnl:+.6f}  trades={token_trades[mint]}  {mint[:20]}...")
