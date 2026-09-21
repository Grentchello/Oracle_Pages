import json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

state_path = Path("/opt/data/hermes_work/bot/base_memecoin/data/state.json")
with state_path.open() as f:
    state = json.load(f)

trades = state.get("trades", [])
positions = state.get("positions", {})
balance = state.get("balance_sol") or state.get("balance_eth") or state.get("balance_usdc")
print(f"Balance: {balance}")
print(f"Open positions: {len(positions)}")
print(f"Total trades in state: {len(trades)}")

log_md = Path("/opt/data/hermes_work/wiki/log.md")
last_eval_ts = None
if log_md.exists():
    txt = log_md.read_text()
    matches = re.findall(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC\] eval", txt)
    if matches:
        last_eval_ts = datetime.strptime(matches[-1], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        print(f"Last eval timestamp: {last_eval_ts}")
    else:
        print("No prior eval header found in log.md")

now = datetime.now(timezone.utc)
print(f"Now (UTC): {now.isoformat()}")

cutoff = last_eval_ts if last_eval_ts else (now - timedelta(hours=2))
print(f"Cutoff: {cutoff.isoformat()}")

new_trades = []
for t in trades:
    exit_ts_str = t.get("exit_time") or t.get("exitTime") or t.get("time")
    if not exit_ts_str:
        continue
    try:
        ts = datetime.fromisoformat(exit_ts_str.replace("Z", "+00:00"))
    except Exception:
        continue
    if ts > cutoff:
        new_trades.append(t)

print(f"Trades since cutoff: {len(new_trades)}")

if new_trades:
    print("Sample trade keys:", list(new_trades[0].keys())[:20])

pnl_key = None
for k in ["pnl_eth", "pnl_sol", "pnl_usdc", "pnl"]:
    if any(k in t for t in new_trades):
        pnl_key = k
        break
print(f"PnL field used: {pnl_key}")

if pnl_key:
    total_pnl = sum(t.get(pnl_key, 0) for t in new_trades)
    print(f"Total PnL since cutoff: {total_pnl:.6f} {pnl_key}")

def categorize(reason, pnl):
    r = (reason or "").lower()
    if "hard cap" in r or "breached" in r or "-50%" in r:
        return "rapid_loss_hardcap"
    if "llm: sell_all" in r and pnl > 0:
        return "tp_or_profit_take"
    if "llm: sell_all" in r and pnl < 0:
        return "override_loss"
    if "llm: sell_half" in r and pnl > 0:
        return "tp_partial"
    if "llm: sell_half" in r and pnl < 0:
        return "override_partial_loss"
    if "sell_all" in r:
        return "override_close"
    if "sell_half" in r:
        return "partial_other"
    return "other"

cats = {}
wins = 0
losses = 0
for t in new_trades:
    pnl = t.get(pnl_key, 0) if pnl_key else 0
    if pnl > 0:
        wins += 1
    elif pnl < 0:
        losses += 1
    c = categorize(t.get("exit_reason", ""), pnl)
    cats[c] = cats.get(c, 0) + 1

total = wins + losses
print(f"\nWin/loss split: wins={wins}, losses={losses}, win_rate={wins/total*100 if total else 0:.1f}%")
print(f"Categorization: {cats}")

winners = sorted(new_trades, key=lambda t: t.get(pnl_key, 0) if pnl_key else 0, reverse=True)[:5]
losers = sorted(new_trades, key=lambda t: t.get(pnl_key, 0) if pnl_key else 0)[:5]
print(f"\nTop 5 winners:")
for t in winners:
    sym = t.get("symbol") or t.get("name") or "?"
    print(f"  {sym:18s} pnl={t.get(pnl_key):+.6f} pct={t.get('pnl_pct', 0):+.1f}% reason={(t.get('exit_reason') or '')[:90]}")
print(f"\nTop 5 losers:")
for t in losers:
    sym = t.get("symbol") or t.get("name") or "?"
    print(f"  {sym:18s} pnl={t.get(pnl_key):+.6f} pct={t.get('pnl_pct', 0):+.1f}% reason={(t.get('exit_reason') or '')[:90]}")

last24 = now - timedelta(hours=24)
t24 = []
for t in trades:
    s = t.get("exit_time")
    if not s:
        continue
    try:
        ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        continue
    if ts > last24:
        t24.append(t)
print(f"\n--- Last 24h ---")
print(f"Trades last 24h: {len(t24)}")
if pnl_key and t24:
    pnl24 = sum(t.get(pnl_key, 0) for t in t24)
    print(f"PnL last 24h: {pnl24:+.6f} {pnl_key}")

print(f"\nState keys: {list(state.keys())}")
for k in ["starting_balance", "starting_balance_sol", "starting_balance_eth", "starting_balance_usdc", "starting_balance_usd"]:
    if k in state:
        print(f"  {k}: {state[k]}")

if trades:
    last_t = max((t for t in trades if t.get("exit_time")), key=lambda t: t.get("exit_time"))
    print(f"\nLast trade exit_time: {last_t.get('exit_time')}")
    sym = last_t.get("symbol") or last_t.get("name")
    print(f"Last trade symbol: {sym}, pnl={last_t.get(pnl_key):+.6f} {pnl_key}")
