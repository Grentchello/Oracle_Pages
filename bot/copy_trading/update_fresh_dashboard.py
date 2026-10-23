#!/usr/bin/env python3
"""Regenerate the 'Fresh Wallets' section of the copy-trading dashboard from today's scan."""
import json
import html
import re
from pathlib import Path

DASH = Path('/opt/data/hermes_work/wiki/projects/copy-trading/dashboard.html')
CACHE = Path('/opt/data/hermes_work/bot/copy_trading/cache/fresh_qualified_today.json')

d = json.loads(CACHE.read_text())
wallets = sorted(d['wallets'], key=lambda x: x.get('score', 0), reverse=True)[:25]
date = d['date']

cards = []
for w in wallets:
    addr = w['wallet']
    funding = w.get('funding', '?')
    tokens = ', '.join(w.get('tokens', []) or [])
    cards.append(f"""<div class="wallet">
  <div class="wallet-header">
    <div class="wallet-address">{addr}<span class="wallet-badge">{html.escape(funding)}</span></div>
    <div class="wallet-links">
      <a href="https://gmgn.ai/sol/address/{addr}" target="_blank">GMGN</a>
      <a href="https://solscan.io/account/{addr}" target="_blank">Solscan</a>
      <a href="https://gmgn.ai/sol/address/{addr}?tab=pnl" target="_blank">PnL</a>
    </div>
  </div>
  <div class="wallet-details">
    <span class="label">PnL:</span> <span class="value positive">{w.get('pnl_sol', 0):.2f} SOL</span>
    <span class="label">&bull; avg buy/trade:</span> <span class="value">{w.get('avg_buy_per_trade', 0):.3f} SOL</span>
    <span class="label">&bull; age:</span> <span class="value">{w.get('age_days', 0):.2f}d</span>
    <span class="label">&bull; score:</span> <span class="value">{w.get('score', 0):.1f}</span><br>
    <span class="label">Tokens:</span> <span class="value">{html.escape(tokens)}</span>
  </div>
</div>""")

block = f"""<div class="wallets">
<h2>🌱 Fresh Wallets — {date}</h2>
<p style="color:#88c0d0; font-size:12px; margin-bottom:12px;">
  New tokens only (history-filtered). {d['tokens_scanned_new']} new tokens scanned &rarr; {d['qualified_wallets']} qualified wallets
  (CEX-funded, profitable, avg buy &le;5 SOL, age &le;60d, PnL 0.5-200 SOL). Top {len(wallets)} by score shown.
</p>
{chr(10).join(cards)}
</div>"""

text = DASH.read_text()
# The fresh-wallets block is the LAST <div class="wallets"> before the trades section.
end = text.index('<div class="trades">')
start = text.rindex('<div class="wallets">', 0, end)
new_text = text[:start] + block + '\n\n' + text[end:]
DASH.write_text(new_text)
print('Dashboard fresh-wallets section updated for', date, 'with', len(wallets), 'wallets')
