// Simulate what the browser does — strip document access
const state = {
  trades: [
    {symbol: "unc", pnl_pct: -20.04, pnl_sol: -0.02006, entry_time: "2026-08-25T13:16:54Z", exit_time: "2026-08-25T13:30:00Z", exit_reason: "stop-loss", post_mortem: {diagnosis: "test"}, partial: false, amount_sold: 100, fraction_sold: 1.0, name: "unc", entry_price_usd: 0.001, exit_price_usd: 0.0008}
  ],
  trade_stats: {total: 1, wins: 0, losses: 1, win_rate_pct: 0, total_pnl_sol: -0.02006, avg_pnl_pct: -20.04, best_pnl_pct: -20.04, worst_pnl_pct: -20.04}
};

const fakeDoc = {
  _writes: {},
  getElementById(id) { return {textContent: '', set innerHTML(v) {this.textContent = v}, set className(v) {}}; },
  querySelectorAll() { return []; }
};

// Stub globals
global.document = fakeDoc;
global.HTMLElement = class {};

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
    return (sec/3600).toFixed(1) + 'h';
  } catch (e) { return '?'; }
}

async function renderTrades(state) {
  const ul = document.getElementById('trades');
  const summary = document.getElementById('trades-summary');
  const trades = (state.trades || []).slice().reverse().slice(0, 20);
  const stats = state.trade_stats || {};

  if (stats.total > 0) {
    const wins = stats.wins || 0;
    const losses = stats.losses || 0;
    const avg = stats.avg_pnl_pct || 0;
    summary.textContent = `${stats.total} trades · ${wins}W/${losses}L · avg ${avg.toFixed(1)}% · best +${stats.best_pnl_pct}% / worst ${stats.worst_pnl_pct}%`;
  } else {
    summary.textContent = 'no closed trades yet';
  }

  if (trades.length === 0) {
    ul.innerHTML = '<li class="loading">No closed trades yet.</li>';
    return;
  }

  ul.innerHTML = trades.map(t => {
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
    return `<li class="trade-item">OK ${sym} ${dur}</li>`;
  }).join('');
}

try {
  renderTrades(state);
  console.log('renderTrades OK');
} catch (e) {
  console.error('renderTrades ERROR:', e.message);
  console.error(e.stack);
}