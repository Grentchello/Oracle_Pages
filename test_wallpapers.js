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

  await page.goto('https://grentchello.github.io/Oracle_Pages/_meta/wallpapers/?nocache=' + Date.now(), {waitUntil: 'networkidle2', timeout: 30000});

  // Count wallpaper cards rendered
  const count = await page.evaluate(() => document.querySelectorAll('.card').length);
  console.log(`Wallpaper cards: ${count}`);

  // Check first 3 image srcs
  const srcs = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.card img')).slice(0, 5).map(i => i.src)
  );
  console.log('First 5 image URLs:');
  srcs.forEach(s => console.log(`  ${s}`));

  // Verify iPhone button filter works
  await page.click('.filter button[data-filter="iphone"]');
  await new Promise(r => setTimeout(r, 500));
  const iphoneCount = await page.evaluate(() => document.querySelectorAll('.card').length);
  console.log(`After iPhone filter: ${iphoneCount} cards`);

  console.log(`\nPage errors: ${errors.length}`);
  errors.forEach(e => console.log(`  ${e}`));

  await browser.close();
})();