const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    args: ['--no-sandbox'],
    headless: true,
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });

  await page.goto('https://grentchello.github.io/Oracle_Pages/projects/trading-pairs/pairs-dashboard.html?nocache=' + Date.now(), {waitUntil: 'networkidle2', timeout: 30000});

  const result = await page.evaluate(() => {
    return {
      bankroll: document.getElementById('tp-bankroll')?.textContent,
      positions: document.getElementById('tp-position-count')?.textContent,
      pnl: document.getElementById('tp-pnl')?.textContent,
      pairCards: document.querySelectorAll('.tp-pair-card').length,
      positionRows: document.querySelectorAll('#tp-positions tbody tr').length,
      strategyLeaderboard: document.querySelectorAll('#tp-leaderboard .tp-leader').length,
      updated: document.getElementById('tp-updated')?.textContent
    };
  });
  console.log('Dashboard state:', JSON.stringify(result, null, 2));
  console.log('\nErrors:', errors.length);
  errors.forEach(e => console.log(' ', e));

  await browser.close();
})();