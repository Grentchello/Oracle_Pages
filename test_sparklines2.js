const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    args: ['--no-sandbox'],
    headless: true,
  });
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE:', msg.text()));
  page.on('pageerror', e => console.log('ERR:', e.message));

  await page.goto('https://grentchello.github.io/Oracle_Pages/trading/?nocache=' + Date.now(), {waitUntil: 'networkidle2'});
  await new Promise(r => setTimeout(r, 3000));

  const debug = await page.evaluate(() => {
    return {
      sparklinesLoaded: window._sparklines ? Object.keys(window._sparklines).length : 'NOT LOADED',
      sampleMint: window._sparklines ? Object.keys(window._sparklines)[0] : null,
      sampleData: window._sparklines ? window._sparklines[Object.keys(window._sparklines)[0]] : null,
      holdingsItems: Array.from(document.querySelectorAll('.position-item')).map(el => ({
        name: el.querySelector('.token-name')?.textContent,
        hasSparkline: !!el.querySelector('.sparkline-cell svg'),
        sparklineHTML: el.querySelector('.sparkline-cell')?.outerHTML?.substring(0, 200)
      }))
    };
  });
  console.log(JSON.stringify(debug, null, 2));

  await browser.close();
})();
