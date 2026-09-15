import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone

with open('/opt/data/hermes_work/wiki/trading/state.json') as f:
    s = json.load(f)

trades = s['trades']
print(f'Total trades: {len(trades)}')


def parse_dt(t, key='exit_time'):
    v = t.get(key) or t.get(key + '_iso')
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace('Z', '+00:00'))
    except Exception:
        return None


# Find last eval timestamp from log.md
try:
    log_tail = subprocess.run(['tail', '-200', '/opt/data/hermes_work/wiki/log.md'],
                              capture_output=True, text=True).stdout
    matches = re.findall(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC\] eval', log_tail)
    last_eval = matches[0] if matches else None
    print(f'Last eval from log: {last_eval}')
except Exception as e:
    last_eval = None
    print(f'log read error: {e}')

if last_eval:
    last_eval_dt = datetime.strptime(last_eval, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
    recent = [t for t in trades if (parse_dt(t, 'exit_time') or datetime.min.replace(tzinfo=timezone.utc)) >= last_eval_dt]
    print(f'Trades since last eval: {len(recent)}')
else:
    now = datetime.now(timezone.utc)
    cutoff = now.replace(hour=max(0, now.hour - 24))
    recent = [t for t in trades if (parse_dt(t, 'exit_time') or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    print(f'No prior eval found, using last 24h: {len(recent)} trades')

print('\n=== RECENT WINDOW ===')
wins = [t for t in recent if t.get('pnl_sol', 0) > 0]
losses = [t for t in recent if t.get('pnl_sol', 0) <= 0]
total_pnl = sum(t.get('pnl_sol', 0) for t in recent)
print(f'  Trades: {len(recent)}')
print(f'  Wins: {len(wins)}  Losses: {len(losses)}')
print(f'  Win rate: {(len(wins)/len(recent)*100 if recent else 0):.1f}%')
print(f'  Net PnL: {total_pnl:+.4f} SOL')
print(f'  Avg win: {(sum(t["pnl_sol"] for t in wins)/len(wins) if wins else 0):+.4f} SOL')
print(f'  Avg loss: {(sum(t["pnl_sol"] for t in losses)/len(losses) if losses else 0):+.4f} SOL')
print(f'  Best trade: {max((t.get("pnl_sol", 0) for t in recent), default=0):+.4f} SOL')
print(f'  Worst trade: {min((t.get("pnl_sol", 0) for t in recent), default=0):+.4f} SOL')

recent_cats = Counter()
for t in recent:
    r = t.get('exit_reason', '')
    if 'ghost' in r.lower() or 'rapid' in r.lower():
        recent_cats['RAPID_LOSS'] += 1
    elif 'hard cap' in r.lower() or 'past the -50' in r.lower() or '-50%' in r.lower():
        recent_cats['HARD_CAP_STOP'] += 1
    elif 'tp' in r.lower() or 'take profit' in r.lower() or 'profit target' in r.lower():
        recent_cats['TP'] += 1
    elif 'override' in r.lower():
        recent_cats['OVERRIDE'] += 1
    elif 'llm: sell' in r.lower() or 'sell_all' in r.lower():
        recent_cats['LLM_SELL'] += 1
    else:
        recent_cats['OTHER'] += 1
print('\nRecent exit categories:')
for cat, n in recent_cats.most_common():
    print(f'  {cat}: {n}')

ghost_count = sum(1 for t in recent if t.get('pnl_pct') == -100.0)
print(f'\nGhost exits (-100%): {ghost_count}')

print('\n=== SLIPPAGE REALITY CHECK ===')
zero_exit = sum(1 for t in recent if t.get('exit_sol_received', 0) == 0)
print(f'Zero-exit (total loss, no SOL recovered) trades: {zero_exit}')
partial = sum(1 for t in recent if t.get('exit_sol_received', 0) > 0 and t.get('pnl_pct', 0) < -50)
print(f'Trades losing >50% but exited with some SOL: {partial}')

print('\n=== ALL-TIME SUMMARY ===')
total_wins = sum(1 for t in trades if t.get('pnl_sol', 0) > 0)
total_losses = sum(1 for t in trades if t.get('pnl_sol', 0) <= 0)
total_pnl_all = sum(t.get('pnl_sol', 0) for t in trades)
print(f'  Total trades: {len(trades)}')
print(f'  Wins: {total_wins}  Losses: {total_losses}')
print(f'  Lifetime PnL: {total_pnl_all:+.4f} SOL')
print(f'  Current balance: {s["balance_sol"]:.4f} SOL (starting {s["starting_balance_sol"]:.2f})')
print(f'  v9.3 reset note: {s["v9_3_hard_reset"].get("reason","")}')

# Categorize ALL-TIME exit reasons too
all_cats = Counter()
for t in trades:
    r = t.get('exit_reason', '')
    if 'ghost' in r.lower() or 'rapid' in r.lower():
        all_cats['RAPID_LOSS'] += 1
    elif 'hard cap' in r.lower() or 'past the -50' in r.lower() or '-50%' in r.lower():
        all_cats['HARD_CAP_STOP'] += 1
    elif 'tp' in r.lower() or 'take profit' in r.lower() or 'profit target' in r.lower():
        all_cats['TP'] += 1
    elif 'override' in r.lower():
        all_cats['OVERRIDE'] += 1
    elif 'llm: sell' in r.lower() or 'sell_all' in r.lower():
        all_cats['LLM_SELL'] += 1
    else:
        all_cats['OTHER'] += 1
print('\n=== ALL-TIME EXIT CATEGORIES ===')
for cat, n in all_cats.most_common():
    pct = n / len(trades) * 100
    print(f'  {cat}: {n} ({pct:.1f}%)')

# Per-trade average position size (entry sol)
positions = [t.get('entry_sol_for_chunk', 0) for t in trades]
import statistics
print(f'\nEntry position sizes — min: {min(positions):.4f}, max: {max(positions):.4f}, mean: {statistics.mean(positions):.4f}, median: {statistics.median(positions):.4f}')