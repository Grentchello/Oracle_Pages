import json

with open('/opt/data/hermes_work/wiki/trading/state.json') as f:
    state = json.load(f)

trades = state['trades']
positions = state['positions']
balance = state['balance_sol']

print(f"Current balance: {balance} SOL")
print(f"Open positions: {len(positions)}")
for mint, pos in positions.items():
    print(f"  - {pos['symbol']}: {pos['entry_sol_spent']} SOL at {pos['entry_time']}")

print(f"\nTotal trades in state.json: {len(trades)}")
print(f"Trades since last eval (idx 3114): {len(trades) - 3114}")

recent = trades[3114:]
print(f"\n=== Trades since last eval (04:42 UTC) ===")
print(f"Count: {len(recent)}")

total_pnl = sum(t['pnl_sol'] for t in recent)
print(f"Net PnL: {total_pnl:+.4f} SOL")

wins = [t for t in recent if t['pnl_sol'] > 0]
losses = [t for t in recent if t['pnl_sol'] <= 0]
print(f"Wins: {len(wins)}, Losses: {len(losses)}")
if len(recent):
    print(f"Win rate: {len(wins)/len(recent)*100:.1f}%")

tp_wins = []
override_wins = []
rapid_losses = []
other_losses = []
for t in recent:
    reason = t.get('exit_reason', '')
    pnl = t['pnl_sol']
    pct = t.get('pnl_pct', 0)
    if pnl > 0:
        if '+50%' in reason or 'partial' in reason.lower() or 'TP' in reason:
            tp_wins.append(t)
        else:
            override_wins.append(t)
    else:
        if pct <= -50 or 'hard cap' in reason.lower() or '-50%' in reason:
            rapid_losses.append(t)
        else:
            other_losses.append(t)

print(f"\nTP wins: {len(tp_wins)} | sum: {sum(t['pnl_sol'] for t in tp_wins):+.4f}")
print(f"Override wins (LLM profit-take): {len(override_wins)} | sum: {sum(t['pnl_sol'] for t in override_wins):+.4f}")
print(f"Rapid losses (<=-50%): {len(rapid_losses)} | sum: {sum(t['pnl_sol'] for t in rapid_losses):+.4f}")
print(f"Other losses: {len(other_losses)} | sum: {sum(t['pnl_sol'] for t in other_losses):+.4f}")

print("\n=== Last 10 trades ===")
for t in trades[-10:]:
    print(f"  {t['exit_time'][:16]} | {t['symbol']:14s} | {t['pnl_pct']:+7.2f}% | {t['pnl_sol']:+.4f} SOL | {t['exit_reason'][:55]}")

print("\n=== Top winners since eval ===")
for t in sorted(wins, key=lambda x: -x['pnl_sol'])[:5]:
    print(f"  {t['symbol']:14s} | {t['pnl_pct']:+7.1f}% | {t['pnl_sol']:+.4f} SOL")

print("\n=== Worst losers since eval ===")
for t in sorted(losses, key=lambda x: x['pnl_sol'])[:5]:
    print(f"  {t['symbol']:14s} | {t['pnl_pct']:+7.1f}% | {t['pnl_sol']:+.4f} SOL")

all_pnl = sum(t['pnl_sol'] for t in trades)
all_wins = sum(1 for t in trades if t['pnl_sol'] > 0)
all_losses_count = len(trades) - all_wins
print(f"\n=== Lifetime (all state.json trades) ===")
print(f"Trades: {len(trades)} | Wins: {all_wins} ({all_wins/len(trades)*100:.1f}%) | Net: {all_pnl:+.4f} SOL")