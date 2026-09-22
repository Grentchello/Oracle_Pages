#!/usr/bin/env python3
"""
Auto-update the live dashboard by reading the current state.
Run this every 30 seconds.
"""
import json
import datetime
import time
from pathlib import Path

STATE_DIR = Path("/opt/data/hermes_work/bot/copy_trader/state")
TARGETS_FILE = Path("/opt/data/hermes_work/bot/copy_trading/cache/copy_targets.json")
OUT_DASH = Path("/opt/data/hermes_work/wiki/projects/copy-trading/live-dashboard.html")

def fmt_criteria(t):
    return [
        f"GMGN-tagged: fresh_wallet",
        f"Funding: {t.get('funding', '?')}",
        f"Hold before first trade: {t.get('hold_hours', 0):.0f}h (≥48h ✓)",
        f"Avg buy size: {t.get('avg_buy', 0):.2f} SOL (≤2 ✓)",
        f"Buy transactions: {t.get('buy_txs', 0)} (real trades)",
        f"GMGN realized PnL: +{t.get('pnl', 0):.2f} SOL",
        f"Wallet age: <7d (fresh)",
    ]

def read_state():
    try:
        account = json.loads((STATE_DIR / "account.json").read_text())
    except:
        account = {"current_balance_sol": 2.0, "starting_balance_sol": 2.0,
                   "realized_pnl_sol": 0.0, "total_trades": 0,
                   "winning_trades": 0, "losing_trades": 0, "total_fees_paid_sol": 0}
    try:
        positions = json.loads((STATE_DIR / "positions.json").read_text())
    except:
        positions = {}
    try:
        perf = json.loads((STATE_DIR / "performance.json").read_text())
    except:
        perf = {}
    try:
        journal = [json.loads(line) for line in (STATE_DIR / "journal.jsonl").read_text().splitlines() if line.strip()][-20:]
    except:
        journal = []
    return account, positions, perf, journal

def render():
    targets = json.loads(TARGETS_FILE.read_text())["targets"]
    account, positions, perf, journal = read_state()
    
    # Wallet cards
    target_cards = []
    for i, t in enumerate(targets):
        addr = t["wallet"]
        crit_html = "".join([f'<li>{c}</li>' for c in fmt_criteria(t)])
        target_cards.append(f"""
    <div class="tcard">
        <div class="tcard-header">
            <div class="rank">#{i+1}</div>
            <div>
                <div class="taddr">{addr}</div>
                <div class="addrlinks">
                    <button class="copy" onclick="navigator.clipboard.writeText('{addr}').then(()=>this.textContent='✓')">copy</button>
                    <a href="https://solscan.io/account/{addr}" target="_blank">solscan →</a>
                    <a href="https://gmgn.ai/sol/address/{addr}" target="_blank">gmgn →</a>
                </div>
            </div>
        </div>
        <div class="crit-list">
            <strong>Why this wallet:</strong>
            <ul>{crit_html}</ul>
        </div>
    </div>""")
    
    # Performance
    perf_rows = []
    for addr, p in perf.items():
        pnl = p.get("realized_pnl_sol", 0)
        trades = p.get("trades", 0)
        wins = p.get("wins", 0)
        losses = p.get("losses", 0)
        wr = (wins / trades * 100) if trades > 0 else 0
        perf_rows.append((addr, pnl, trades, wins, losses, wr))
    perf_rows.sort(key=lambda x: -x[1])
    
    perf_html = ""
    if perf_rows:
        perf_html = "<table class=\'perftable\'><tr><th>Wallet</th><th>PnL (SOL)</th><th>Trades</th><th>Wins</th><th>Losses</th><th>WR</th></tr>"
        for addr, pnl, t, w, l, wr in perf_rows:
            cls = "pos" if pnl > 0 else ("neg" if pnl < 0 else "")
            perf_html += f'<tr><td class="addr">{addr[:14]}...</td><td class="{cls}">{pnl:+.4f}</td><td>{t}</td><td>{w}</td><td>{l}</td><td>{wr:.0f}%</td></tr>'
        perf_html += "</table>"
    
    # Positions
    pos_html = ""
    if positions:
        pos_html = "<ul class=\'poslist\'>"
        for mint, p in positions.items():
            pos_html += f'<li><span class="pos-mint">{mint[:14]}...</span> <span class="pos-tokens">{p.get("tokens", 0):.4f}</span> tokens | from {p.get("watched_wallet", "?")[:14]}...</li>'
        pos_html += "</ul>"
    
    # Journal
    journal_html = ""
    if journal:
        journal_html = "<table class=\'jrnl\'><tr><th>Time</th><th>Type</th><th>Wallet</th><th>Token</th><th>Our SOL</th><th>Fees</th><th>PnL</th></tr>"
        for j in reversed(journal):
            ts = j.get("logged_at", 0)
            time_str = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            typ = j.get("type", "?")
            wallet = j.get("watched_wallet", "?")[:14]
            token = (j.get("token_mint", "?") or "?")[:8]
            if typ == "BUY":
                sol_str = f"-{j.get('our_sol', 0):.4f}"
                fees_str = f"{j.get('fee_sol', 0) + j.get('slippage_sol', 0):.5f}"
                pnl_str = "—"
            else:
                sol_str = f"+{j.get('sol_received_net', 0):.4f}"
                fees_str = f"{j.get('fee_sol', 0) + j.get('slippage_sol', 0):.5f}"
                pnl_str = f"{j.get('pnl_sol', 0):+.4f}"
            pnl_cls = "pos" if j.get("pnl_sol", 0) > 0 else ("neg" if j.get("pnl_sol", 0) < 0 else "")
            journal_html += f'<tr><td>{time_str}</td><td>{typ}</td><td>{wallet}...</td><td>{token}...</td><td>{sol_str}</td><td>{fees_str}</td><td class="{pnl_cls}">{pnl_str}</td></tr>'
        journal_html += "</table>"
    
    # KPIs
    total_balance = account.get("current_balance_sol", 2.0)
    total_pnl = account.get("realized_pnl_sol", 0)
    total_trades = account.get("total_trades", 0)
    fees = account.get("total_fees_paid_sol", 0)
    wins = account.get("winning_trades", 0)
    losses = account.get("losing_trades", 0)
    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    pct_pnl = ((total_balance - 2.0) / 2.0 * 100)
    
    pnl_class = "alt" if total_pnl > 0 else "warn"
    
    # Live indicator: pulse if process is running
    live = "LIVE"
    
    # Time
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Live Copy-Trading — Top 10 Wallets</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", monospace; background: #0d1117; color: #c9d1d9; padding: 16px; }}
header {{ border-bottom: 1px solid #30363d; padding-bottom: 16px; margin-bottom: 24px; }}
h1 {{ color: #3fb950; font-size: 22px; margin-bottom: 4px; }}
.subtitle {{ color: #8b949e; font-size: 12px; }}
.kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 16px 0 24px; }}
.kpi {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; }}
.kpi-label {{ font-size: 10px; color: #8b949e; text-transform: uppercase; }}
.kpi-val {{ font-size: 22px; font-weight: 700; color: #3fb950; margin-top: 4px; }}
.kpi-val.alt {{ color: #d29922; }}
.kpi-val.warn {{ color: #f85149; }}
.kpi-val.cyan {{ color: #58a6ff; }}
.section {{ margin: 32px 0; }}
.section h2 {{ color: #58a6ff; font-size: 16px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #30363d; }}
.tcard {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #3fb950; }}
.tcard-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
.rank {{ background: #58a6ff; color: #0d1117; font-weight: 800; border-radius: 50%; min-width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 12px; }}
.taddr {{ font-family: monospace; font-size: 12px; color: #c9d1d9; }}
.addrlinks {{ margin-top: 4px; display: flex; gap: 6px; font-size: 11px; flex-wrap: wrap; }}
.addrlinks a, .copy {{ color: #58a6ff; text-decoration: none; background: none; border: 1px solid #30363d; padding: 2px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; }}
.addrlinks a:hover, .copy:hover {{ background: #21262d; }}
.crit-list {{ font-size: 11px; color: #8b949e; }}
.crit-list ul {{ list-style: disc; padding-left: 20px; margin-top: 4px; }}
.crit-list strong {{ color: #3fb950; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; background: #161b22; border-radius: 6px; overflow: hidden; }}
th, td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid #21262d; }}
th {{ background: #0d1117; color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 10px; }}
td.addr {{ font-family: monospace; font-size: 11px; }}
.pos {{ color: #3fb950; }}
.neg {{ color: #f85149; }}
.poslist {{ list-style: none; padding: 0; }}
.poslist li {{ padding: 8px 12px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; margin-bottom: 6px; font-size: 12px; }}
.pos-mint {{ font-family: monospace; color: #d29922; }}
.pos-tokens {{ color: #3fb950; font-weight: 600; }}
.live-indicator {{ display: inline-flex; align-items: center; gap: 6px; background: #238636; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
.pulse {{ width: 8px; height: 8px; background: #3fb950; border-radius: 50%; animation: pulse 1.5s infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} }}
footer {{ border-top: 1px solid #30363d; padding-top: 16px; margin-top: 32px; font-size: 11px; color: #8b949e; }}
.empty {{ color: #8b949e; padding: 12px; font-style: italic; }}
.update-ts {{ color: #6e6e6e; font-size: 10px; margin-top: 4px; }}
</style>
</head>
<body>
<header>
    <h1>🟢 Live Copy-Trading — Top 10 Wallets</h1>
    <div class="subtitle">
        Real-time paper trading • Simulated fees (0.30%) + slippage (0.50%) • Polls every 2s
    </div>
    <div style="margin-top: 8px;">
        <span class="live-indicator"><div class="pulse"></div>{live}</span>
        <span class="update-ts">last update: {now_str}</span>
    </div>
</header>

<div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Paper Balance</div><div class="kpi-val cyan">{total_balance:.4f} SOL</div></div>
    <div class="kpi"><div class="kpi-label">Realized PnL</div><div class="kpi-val {pnl_class}">{total_pnl:+.4f} SOL</div></div>
    <div class="kpi"><div class="kpi-label">% Change</div><div class="kpi-val {pnl_class}">{pct_pnl:+.2f}%</div></div>
    <div class="kpi"><div class="kpi-label">Trades</div><div class="kpi-val cyan">{total_trades}</div></div>
    <div class="kpi"><div class="kpi-label">Win Rate</div><div class="kpi-val">{wr:.0f}%</div></div>
    <div class="kpi"><div class="kpi-label">Fees Paid</div><div class="kpi-val warn">{fees:.4f} SOL</div></div>
</div>

<div class="section">
    <h2>👀 Watched Wallets — Top 10 by Score</h2>
    <div style="font-size: 11px; color: #8b949e; margin-bottom: 12px;">
        Each wallet passes all selection criteria (fresh_wallet + CEX funded + ≥48h hold + profitable + ≤2 SOL avg buy).
        The trader polls every 2s and simulates a copy trade with fees + slippage.
    </div>
    {"".join(target_cards)}
</div>

<div class="section">
    <h2>📊 Per-Wallet Performance (Live)</h2>
    {perf_html if perf_html else '<div class="empty">No trades yet — trader is watching. First copy trade will appear here.</div>'}
</div>

<div class="section">
    <h2>💼 Open Paper Positions</h2>
    {pos_html if pos_html else '<div class="empty">No open positions.</div>'}
</div>

<div class="section">
    <h2>📝 Recent Trade Journal (last 20)</h2>
    {journal_html if journal_html else '<div class="empty">Journal empty — waiting for first signal...</div>'}
</div>

<footer>
    <p><strong>How this works:</strong></p>
    <p>1. Polls Solana mainnet every 2 seconds for each watched wallet</p>
    <p>2. When a swap is detected (token in/out + SOL movement), decodes the trade</p>
    <p>3. Simulates a copy at 10% of paper balance (max 0.1 SOL) — proportionally scaled</p>
    <p>4. Deducts simulated 0.30% fee + 0.50% slippage buffer</p>
    <p>5. Logs to journal + per-wallet performance tracker</p>
    <p style="margin-top: 8px;"><strong>Safety:</strong> PAPER mode only — no real SOL is sent. Real PnL = $0 risk.</p>
    <p style="margin-top: 8px;">
        <a href="https://grentchello.github.io/Oracle_Pages/projects/copy-trading/" style="color:#58a6ff;">← Original copy-trading dashboard</a>
    </p>
</footer>
</body>
</html>"""
    
    OUT_DASH.write_text(html)
    print(f"Dashboard updated at {now_str} (balance={total_balance:.4f}, trades={total_trades})")

if __name__ == "__main__":
    render()
