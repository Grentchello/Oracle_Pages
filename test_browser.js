// Simulate the full browser environment
const fs = require('fs');
const html = fs.readFileSync('/tmp/now.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// Stub browser environment
const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) {
      elements.set(id, {
        textContent: '',
        innerHTML: '',
        className: '',
        style: {},
        title: '',
        textContent_: '',
        set textContent(v) { this.textContent_ = v; },
        get textContent() { return this.textContent_; },
        querySelector() { return null; },
        querySelectorAll() { return []; }
      });
    }
    return elements.get(id);
  }
};
global.document = document;
global.window = { WebSocket: class { constructor() { throw new Error('WebSocket blocked in test'); } } };
global.fetch = async (url) => {
  // Serve the actual files
  const u = url.split('?')[0];
  if (u.endsWith('state.json')) {
    return { ok: true, text: async () => fs.readFileSync('/opt/data/hermes_work/wiki/trading/state.json', 'utf8') };
  }
  if (u.endsWith('watchlist.json')) {
    return { ok: true, text: async () => fs.readFileSync('/opt/data/hermes_work/wiki/trading/watchlist.json', 'utf8') };
  }
  return { ok: false, text: async () => '' };
};

// Mock console.error to capture errors
const errors = [];
const origError = console.error;
console.error = (...args) => {
  errors.push(args.map(a => String(a)).join(' ').slice(0, 300));
  origError.apply(console, args);
};

// Run the script in async wrapper
async function run() {
  try {
    await eval(`(async () => { ${script} })()`);
  } catch (e) {
    console.log('Top-level error:', e.message);
  }
  // Wait a bit for async
  await new Promise(r => setTimeout(r, 500));

  // Check what got rendered
  console.log('=== After execution ===');
  console.log('Errors caught:', errors);
  console.log('trades-summary textContent:', document.getElementById('trades-summary').textContent);
  console.log('trades innerHTML (first 200):', document.getElementById('trades').innerHTML.slice(0, 200));
  console.log('holdings innerHTML (first 200):', document.getElementById('holdings').innerHTML.slice(0, 200));
  console.log('watchlist innerHTML (first 100):', document.getElementById('watchlist').innerHTML.slice(0, 100));
  console.log('decisions innerHTML (first 100):', document.getElementById('decisions').innerHTML.slice(0, 100));
  console.log('learning innerHTML (first 100):', document.getElementById('learning').innerHTML.slice(0, 100));
}

run().catch(e => console.error('Test failed:', e));