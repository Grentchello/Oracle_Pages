const fs = require('fs');
const state = JSON.parse(fs.readFileSync('/opt/data/hermes_work/wiki/trading/state.json', 'utf8'));
const watchlist = JSON.parse(fs.readFileSync('/opt/data/hermes_work/wiki/trading/watchlist.json', 'utf8'));

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function fmtUSD(v) {
  if (v == null || isNaN(v)) return '—';
  if (Math.abs(v) >= 1) return '$' + v.toFixed(2);
  return '$' + v.toFixed(6);
}
function fmtTime(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toISOString().slice(0,16).replace('T', ' '); } catch (e) { return '—'; }
}
function computeDuration(start, end) {
  try {
    const s = new Date(start), e = new Date(end);
    const sec = Math.round((e - s) / 1000);
    if (sec < 3600) return Math.round(sec/60) + 'm';
    if (sec < 86400) return (sec/3600).toFixed(1) + 'h';
    return (sec/86400).toFixed(1) + 'd';
  } catch (e) { return '?'; }
}

function renderTrades(state) {
  const trades = (state.trades || []).slice().reverse().slice(0, 20);
  const stats = state.trade_stats || {};
  console.log('trades length:', trades.length);
  console.log('stats.total:', stats.total);

  if (stats.total > 0) {
    const wins = stats.wins || 0;
    const losses = stats.losses || 0;
    const avg = stats.avg_pnl_pct || 0;
    console.log('avg.toFixed(1):', avg.toFixed(1));
    console.log('best:', stats.best_pnl_pct, 'worst:', stats.worst_pnl_pct);
  }

  if (trades.length === 0) {
    console.log('No trades to render');
    return;
  }

  try {
    const html = trades.map(t => {
      const pnlPct = parseFloat(t.pnl_pct);
      const cls = pnlPct >= 0 ? 'pos' : 'neg';
      const sign = pnlPct >= 0 ? '+' : '';
      const entryT = fmtTime(t.entry_time);
      const exitT = fmtTime(t.exit_time);
      const exitReason = escapeHtml(t.exit_reason || 'exit');
      const sym = escapeHtml(t.symbol || '?');
      const name = escapeHtml((t.name || '').slice(0,24));
      const dur = computeDuration(t.entry_time, t.exit_time);
      const partialBadge = t.partial ? '<span class="partial-badge">partial</span> ' : '';
      const diagnosis = t.post_mortem && t.post_mortem.diagnosis ? escapeHtml(t.post_mortem.diagnosis) : '';
      return `<li class="trade-item">${sym} ${dur} ${pnlPct.toFixed(1)}%</li>`;
    }).join('');
    console.log('Rendered HTML:', html);
  } catch (e) {
    console.error('ERROR in render:', e.message);
    console.error(e.stack);
  }
}

renderTrades(state);