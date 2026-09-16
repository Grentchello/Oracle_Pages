import json, datetime
state = json.load(open('/opt/data/hermes_work/wiki/trading/state.json'))
trades = state['trades']

LAST_EVAL = datetime.datetime.fromisoformat('2026-09-16T20:19:00+00:00').timestamp()
PREV_EVAL = datetime.datetime.fromisoformat('2026-09-15T01:43:00+00:00').timestamp()

def exit_ts(t):
    return datetime.datetime.fromisoformat(t['exit_time']).timestamp()

since_last = [t for t in trades if exit_ts(t) > LAST_EVAL]
between   = [t for t in trades if PREV_EVAL < exit_ts(t) <= LAST_EVAL]
alltime   = trades

def stats(subset, label):
    pnls = [t['pnl_sol'] for t in subset]
    net = sum(pnls) if pnls else 0
    wins = [t for t in subset if t['pnl_sol'] > 0]
    losses = [t for t in subset if t['pnl_sol'] <= 0]
    wr = (len(wins)/len(subset)*100) if subset else 0
    partial = sum(1 for t in subset if t['partial'])
    hard = sum(1 for t in subset if 'hard cap' in (t.get('exit_reason','') or '').lower()
                                   or '-50%' in (t.get('exit_reason','') or '')
                                   or 'breached' in (t.get('exit_reason','') or '').lower())
    ghost = sum(1 for t in subset if 'ghost' in (t.get('exit_reason','') or '').lower()
                                   or 'rapid' in (t.get('exit_reason','') or '').lower()
                                   or '-15%' in (t.get('exit_reason','') or ''))
    print(f'=== {label} ===')
    print(f'  count={len(subset)}  net_pnl_sol={net:+.4f}  avg_pnl={net/len(subset):+.5f}' if subset else f'  count=0')
    print(f'  wins={len(wins)}  losses={len(losses)}  WR={wr:.1f}%')
    print(f'  partial={partial}  hard_stop={hard}  ghost={ghost}')
    if subset:
        b = max(subset, key=lambda t: t['pnl_sol']); w = min(subset, key=lambda t: t['pnl_sol'])
        print(f'  biggest: {b["symbol"]} {b["pnl_sol"]:+.4f} SOL ({b["pnl_pct"]:+.1f}%)')
        print(f'  worst  : {w["symbol"]} {w["pnl_sol"]:+.4f} SOL ({w["pnl_pct"]:+.1f}%)')

stats(since_last, 'WINDOW: since last eval (Sep 16 20:19 -> now)')
print()
stats(between, 'WINDOW: between Sep 15 01:43 and Sep 16 20:19 (the prior 36h gap)')
print()
stats(alltime, 'ALL-TIME')

print()
print('balance_sol:', state['balance_sol'])
print('open positions:', len(state['positions']))

print()
print('Last 10 trades by exit_time:')
for t in trades[-10:]:
    print(f"  {t['exit_time'][:19]}  {t['symbol']:<10}  pnl={t['pnl_sol']:+.4f}  pct={t['pnl_pct']:+.1f}%  par={t['partial']}")
