import json
from datetime import datetime, timezone

with open('/opt/data/hermes_work/wiki/trading/state.json') as f:
    s = json.load(f)

trades = s['trades']
balance = s['balance_sol']

last_eval = datetime(2026, 9, 17, 0, 23, 0, tzinfo=timezone.utc)
recent = [t for t in trades if datetime.fromisoformat(t['exit_time']) > last_eval]

print(f"=== WINDOW: 2026-09-17 00:23 UTC -> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} ===")
print(f"Total trades in state.json: {len(trades)}")
print(f"Trades since last eval: {len(recent)}")
print(f"Current balance: {balance:.6f} SOL")
print(f"Open positions: {len(s.get('positions', {}))}")

if not recent:
    print("\nNo new trades in window.")
else:
    total_pnl = sum(t['pnl_sol'] for t in recent)
    wins = [t for t in recent if t['pnl_sol'] > 0]
    losses = [t for t in recent if t['pnl_sol'] <= 0]
    ghost_count = sum(1 for t in recent if 'GHOST' in t.get('exit_reason','') or 'ghost' in t.get('exit_reason','').lower())
    ghost_pnl = sum(t['pnl_sol'] for t in recent if 'GHOST' in t.get('exit_reason','') or 'ghost' in t.get('exit_reason','').lower())

    print(f"\nNet realized PnL: {total_pnl:+.4f} SOL")
    print(f"Win rate: {len(wins)/len(recent)*100:.1f}% ({len(wins)} W / {len(losses)} L)")
    print(f"Ghost exits: {ghost_count} ({ghost_count/len(recent)*100:.1f}%), sum {ghost_pnl:+.4f} SOL")

    tp_wins = [t for t in recent if t['pnl_sol'] > 0 and ('+50%' in t.get('exit_reason','') or 'auto-v8.7 TP' in t.get('exit_reason',''))]
    override_wins = [t for t in recent if t['pnl_sol'] > 0 and t not in tp_wins]
    rapid_losses = [t for t in recent if t['pnl_sol'] < 0 and (t.get('pnl_pct', 0) <= -50 or 'hard cap' in t.get('exit_reason','').lower() or '-50%' in t.get('exit_reason',''))]
    other_losses = [t for t in recent if t['pnl_sol'] <= 0 and t not in rapid_losses]

    print(f"\nTP wins:        {len(tp_wins):3d} | sum {sum(t['pnl_sol'] for t in tp_wins):+.4f}")
    print(f"Override wins:  {len(override_wins):3d} | sum {sum(t['pnl_sol'] for t in override_wins):+.4f}")
    print(f"Rapid losses:   {len(rapid_losses):3d} | sum {sum(t['pnl_sol'] for t in rapid_losses):+.4f}")
    print(f"Other losses:   {len(other_losses):3d} | sum {sum(t['pnl_sol'] for t in other_losses):+.4f}")

    real_exits = [t for t in recent if not ('GHOST' in t.get('exit_reason','') or 'ghost' in t.get('exit_reason','').lower())]
    real_wins = [t for t in real_exits if t['pnl_sol'] > 0]
    if real_exits:
        print(f"\nReal exits only (n={len(real_exits)}): WR {len(real_wins)/len(real_exits)*100:.1f}%, sum {sum(t['pnl_sol'] for t in real_exits):+.4f} SOL")

    print("\n=== Last 10 trades ===")
    for t in recent[-10:]:
        print(f"  {t['exit_time'][:16]} | {t['symbol']:12s} | {t['pnl_pct']:+7.2f}% | {t['pnl_sol']:+.4f} | {t['exit_reason'][:55]}")

    last_eval_balance = 1.54444
    balance_delta = balance - last_eval_balance
    print(f"\n=== Balance movement ===")
    print(f"Last eval balance: {last_eval_balance:.4f} SOL")
    print(f"Current balance:   {balance:.4f} SOL")
    print(f"Delta:             {balance_delta:+.4f} SOL")

    cum_pnl = sum(t['pnl_sol'] for t in trades)
    print(f"\nLifetime realized PnL: {cum_pnl:+.4f} SOL across {len(trades)} trades")