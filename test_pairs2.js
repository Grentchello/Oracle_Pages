const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    args: ['--no-sandbox'],
    headless: true,
  });
  const page = await browser.newPage();
  page.on('response', resp => {
    if (resp.status() >= 400) console.log(`HTTP ${resp.status()}: ${resp.url()}`);
  });

  await page.goto('https://grentchello.github.io/Oracle_Pages/projects/trading-pairs/pairs-dashboard.html?nocache=' + Date.now(), {waitUntil: 'networkidle2', timeout: 30000});
  console.log('done');
  await browser.close();
})();