// Real browser test using puppeteer-core with the existing chromium binary
const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 }); // iPhone 12 viewport

  const consoleLogs = [];
  const pageErrors = [];
  page.on('console', m => consoleLogs.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', e => pageErrors.push(`[pageerror] ${e.message}\n${e.stack}`));
  page.on('requestfailed', r => pageErrors.push(`[requestfailed] ${r.url()} - ${r.failure().errorText}`));

  console.log('Loading https://grentchello.github.io/Oracle_Pages/trading/?nocache=' + Date.now());
  await page.goto('https://grentchello.github.io/Oracle_Pages/trading/?nocache=' + Date.now(), {
    waitUntil: 'networkidle2',
    timeout: 30000,
  });

  // Wait a bit for WS to connect
  await new Promise(r => setTimeout(r, 3000));

  // Capture state
  const state = await page.evaluate(() => {
    return {
      tradesSummary: document.getElementById('trades-summary')?.textContent || 'NOT FOUND',
      tradesInner: document.getElementById('trades')?.innerHTML?.slice(0, 300) || 'NOT FOUND',
      holdingsInner: document.getElementById('holdings')?.innerHTML?.slice(0, 200) || 'NOT FOUND',
      watchlistInner: document.getElementById('watchlist')?.innerHTML?.slice(0, 200) || 'NOT FOUND',
      decisionsInner: document.getElementById('decisions')?.innerHTML?.slice(0, 200) || 'NOT FOUND',
      learningInner: document.getElementById('learning')?.innerHTML?.slice(0, 200) || 'NOT FOUND',
      errorBanner: document.getElementById('error-banner')?.textContent || '',
      liveStatus: document.getElementById('live-status')?.textContent || '',
    };
  });

  console.log('=== RENDERED STATE ===');
  console.log('trades-summary:', state.tradesSummary);
  console.log('trades innerHTML:', state.tradesInner);
  console.log('---');
  console.log('holdings:', state.holdingsInner);
  console.log('---');
  console.log('watchlist:', state.watchlistInner);
  console.log('---');
  console.log('decisions:', state.decisionsInner);
  console.log('---');
  console.log('learning:', state.learningInner);
  console.log('---');
  console.log('live-status:', state.liveStatus);
  console.log('error-banner:', state.errorBanner);

  console.log('\n=== CONSOLE LOGS ===');
  consoleLogs.forEach(l => console.log(l));

  console.log('\n=== PAGE ERRORS ===');
  if (pageErrors.length === 0) console.log('(none)');
  pageErrors.forEach(e => console.log(e));

  await browser.close();
})().catch(e => { console.error('TEST FAILED:', e); process.exit(1); });