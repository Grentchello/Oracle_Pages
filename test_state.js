const fs = require('fs');
const stateJson = fs.readFileSync('/opt/data/hermes_work/wiki/trading/state.json', 'utf8');
const state = JSON.parse(stateJson);
console.log('state.trade_stats.total:', state.trade_stats?.total);
console.log('Object.keys(state.trade_stats):', Object.keys(state.trade_stats || {}));
console.log('state.trade_stats.learning:', state.trade_stats?.learning);
console.log('Has state.trades:', Array.isArray(state.trades), 'length:', state.trades?.length);