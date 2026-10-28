#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

d = json.loads(Path('/opt/data/hermes_work/bot/copy_trading/cache/fresh_qualified_today.json').read_text())
ws = d['wallets']
fund = Counter(w.get('funding', '?') for w in ws)
total_pnl = sum(w.get('pnl_sol', 0) for w in ws)
print('date', d['date'])
print('tokens', d['tokens_scanned_new'], 'qualified', d['qualified_wallets'])
print('funding', dict(fund))
print('total_pnl', round(total_pnl, 2))
for w in sorted(ws, key=lambda x: x.get('pnl_sol', 0), reverse=True)[:5]:
    print(f"{w['wallet']} | {w.get('pnl_sol',0):.2f} SOL | {w.get('funding')} | score {w.get('score',0):.1f} | {','.join(w.get('tokens',[]))} | age {w.get('age_days',0):.2f}d | avgbuy {w.get('avg_buy_per_trade',0):.2f}")
