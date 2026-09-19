import json
from datetime import datetime, timezone

with open('/opt/data/hermes_work/wiki/trading/state.json') as f:
    state = json.load(f)

trades = state['trades']
balance = state['balance_sol']
now = datetime.now(timezone.utc)

cutoff_2h = now.timestamp() - 2*3600
recent_2h = [t for t in trades if datetime.fromisoformat(t['exit_time']).timestamp() > cutoff_2h]
print(f"Trades in last 2h: {len(recent_2h)}")
print(f"Balance: {balance} SOL")
print(f"Positions: {len(state.get('positions', {}))}")
print(f"Last trade exit: {trades[-1]['exit_time'] if trades else 'none'}")

cutoff_reset = datetime(2026, 9, 15, tzinfo=timezone.utc).timestamp()
post_reset = [t for t in trades if datetime.fromisoformat(t['exit_time']).timestamp() > cutoff_reset]
print(f"Post-reset (Sep 15+) trades: {len(post_reset)}")
if post_reset:
    pnl = sum(t['pnl_sol'] for t in post_reset)
    wins = sum(1 for t in post_reset if t['pnl_sol'] > 0)
    print(f"  PnL: {pnl:.4f} SOL, W={wins}/{len(post_reset)} ({wins/len(post_reset)*100:.1f}%)")
print(f"All-time PnL: {sum(t['pnl_sol'] for t in trades):.4f} SOL (inflated by slippage sim)")
