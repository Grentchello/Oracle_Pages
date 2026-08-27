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
  page.on('response', resp => {
    if (resp.status() >= 400) console.log(`HTTP ${resp.status()}: ${resp.url()}`);
  });

  await page.goto('https://grentchello.github.io/Oracle_Pages/trading/?nocache=' + Date.now(), {waitUntil: 'networkidle2', timeout: 30000});
  // Wait for sparkline to render
  await new Promise(r => setTimeout(r, 2000));

  const result = await page.evaluate(() => {
    const holdings = document.querySelectorAll('.position-item');
    const sparklines = document.querySelectorAll('.sparkline-cell svg');
    const holdingsText = Array.from(holdings).map(h => h.querySelector('.token-name')?.textContent);
    return {
      holdingsCount: holdings.length,
      sparklineCount: sparklines.length,
      holdingsText: holdingsText.slice(0, 5)
    };
  });
  console.log('Dashboard state:', JSON.stringify(result, null, 2));
  console.log('\nErrors:', errors.length);
  errors.forEach(e => console.log(' ', e));

  await browser.close();
})();