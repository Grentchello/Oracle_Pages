// Simulate what the browser does
const state = {
  trades: [
    {symbol: "unc", pnl_pct: -20.04, pnl_sol: -0.02006, entry_time: "2026-08-25T13:16:54Z", exit_time: "2026-08-25T13:30:00Z", exit_reason: "stop-loss", post_mortem: {diagnosis: "test"}, partial: false, amount_sold: 100, fraction_sold: 1.0, name: "unc", entry_price_usd: 0.001, exit_price_usd: 0.0008}
  ],
  trade_stats: {total: 1, wins: 0, losses: 1, win_rate_pct: 0, total_pnl_sol: -0.02006, avg_pnl_pct: -20.04, best_pnl_pct: -20.04, worst_pnl_pct: -20.04}
};

// Try the same code as renderTrades
async function renderTrades(state) {
  const ul = document; // fake
  const summary = document; // fake
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
    return;
  }
  const result = trades.map(t => {
    const pnlPct = parseFloat(t.pnl_pct);
    const cls = pnlPct >= 0 ? 'pos' : 'neg';
    const sign = pnlPct >= 0 ? '+' : '';
    return {pnlPct, sign, sol: t.pnl_sol.toFixed(4)};
  });
  console.log('renderTrades OK', result);
}

try {
  renderTrades(state);
} catch (e) {
  console.error('renderTrades ERROR:', e.message);
  console.error(e.stack);
}