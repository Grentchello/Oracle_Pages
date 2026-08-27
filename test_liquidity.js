const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    args: ['--no-sandbox'],
    headless: true,
  });
  const page = await browser.newPage();
  await page.goto('https://grentchello.github.io/Oracle_Pages/trading/?nocache=' + Date.now(), {waitUntil: 'networkidle2'});
  const result = await page.evaluate(() => {
    const items = Array.from(document.querySelectorAll('.position-item'));
    return items.map(item => ({
      name: item.querySelector('.token-name')?.textContent,
      meta: item.querySelector('.token-meta')?.textContent,
      badge: item.querySelector('.liquidity-badge')?.textContent || null,
      badgeClass: item.querySelector('.liquidity-badge')?.className || null
    }));
  });
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
})();