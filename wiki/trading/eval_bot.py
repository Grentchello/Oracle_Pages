import json
from collections import Counter
from datetime import datetime

with open('/opt/data/hermes_work/wiki/trading/state.json') as f:
    state = json.load(f)

trades = state['trades']
today_trades = [t for t in trades if t['exit_time'].startswith('2026-09-13')]

print("=== BIG WINNERS TODAY ===")
for t in today_trades:
    if t['pnl_sol'] > 0.5:
        print(f"\n{t['symbol']}: +{t['pnl_sol']:.4f} SOL ({t['pnl_pct']:+.1f}%)")
        print(f"  Entry: {t['entry_time']} @ ${t['entry_price_usd']:.3e}")
        print(f"  Exit:  {t['exit_time']} @ ${t['exit_price_usd']:.3e}")
        print(f"  Reason: {t['exit_reason'][:200]}")

print("\n=== LOSS DISTRIBUTION TODAY ===")
losses = [t for t in today_trades if t['pnl_sol'] < 0]
loss_pcts = [t['pnl_pct'] for t in losses]
loss_pcts.sort()
print(f"  Total losses: {len(losses)}")
print(f"  Median loss %: {loss_pcts[len(loss_pcts)//2]:.1f}")
print(f"  Avg loss %: {sum(loss_pcts)/len(loss_pcts):.1f}")
print(f"  Loss <= -20%: {sum(1 for p in loss_pcts if p <= -20)}")
print(f"  Loss <= -40%: {sum(1 for p in loss_pcts if p <= -40)}")
print(f"  Loss <= -50%: {sum(1 for p in loss_pcts if p <= -50)}")

print("\n=== HOLD TIME FOR LOSSES TODAY ===")
fast_drops = 0
slow_bleeds = 0
hold_times = []
for t in losses:
    entry = datetime.fromisoformat(t['entry_time'].replace('Z','+00:00'))
    exit_t = datetime.fromisoformat(t['exit_time'].replace('Z','+00:00'))
    hold_mins = (exit_t - entry).total_seconds() / 60
    hold_times.append(hold_mins)
    if hold_mins < 10:
        fast_drops += 1
    elif hold_mins > 60:
        slow_bleeds += 1
hold_times.sort()
print(f"  Fast drops (<10 min): {fast_drops}/{len(losses)}")
print(f"  Slow bleeds (>60 min): {slow_bleeds}/{len(losses)}")
print(f"  Median hold min: {hold_times[len(hold_times)//2]:.1f}")

print("\n=== HARD STOP ANALYSIS ===")
hard_stops = [t for t in losses if 'past the -50%' in t.get('exit_reason','') or 'breached the hard -50%' in t.get('exit_reason','') or '-50% hard cap' in t.get('exit_reason','')]
print(f"Hard-stop -50% losses: {len(hard_stops)}")
if hard_stops:
    avg_hold = sum((datetime.fromisoformat(t['exit_time'].replace('Z','+00:00')) -
                    datetime.fromisoformat(t['entry_time'].replace('Z','+00:00'))).total_seconds()/60
                   for t in hard_stops) / len(hard_stops)
    print(f"  Avg hold to -50% cap: {avg_hold:.1f} min")

print("\n=== SLIPPAGE-ADJUSTED VIEW ===")
total_pnl = sum(t['pnl_sol'] for t in today_trades)
profit_trades = [t for t in today_trades if t['pnl_sol'] > 0]
slippage_loss = sum(t['pnl_sol'] * 0.20 for t in profit_trades)
adjusted_pnl = total_pnl - slippage_loss
print(f"  Reported PnL: {total_pnl:+.4f} SOL")
print(f"  Slippage haircut (20% on wins): -{slippage_loss:.4f} SOL")
print(f"  Conservative PnL: {adjusted_pnl:+.4f} SOL")

total_profit_from_wins = sum(t['pnl_sol'] for t in profit_trades)
top2_pct = sorted([t['pnl_sol'] for t in profit_trades], reverse=True)[:2]
top2_pct_sum = sum(top2_pct)
print(f"\n  Top 2 winners: +{top2_pct_sum:.4f} SOL ({top2_pct_sum/total_profit_from_wins*100:.1f}% of all wins)")

print("\n=== POSITION SIZES TODAY ===")
sizes = Counter()
for t in today_trades:
    s = round(t.get('entry_sol_for_chunk', 0), 4)
    sizes[s] += 1
for k, v in sizes.most_common(10):
    print(f"  {k} SOL: {v} trades")