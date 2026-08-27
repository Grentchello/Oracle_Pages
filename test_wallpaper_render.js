const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    args: ['--no-sandbox'],
    headless: true,
  });

  const page = await browser.newPage();
  const logs = [];
  const errors = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('https://grentchello.github.io/Oracle_Pages/_meta/wallpapers/?nocache=' + Date.now(), {waitUntil: 'networkidle2', timeout: 30000});

  const result = await page.evaluate(() => {
    const cards = document.querySelectorAll('.card');
    const cardImages = document.querySelectorAll('.card img');
    return {
      cardCount: cards.length,
      cardImageCount: cardImages.length,
      firstCardHTML: cards[0] ? cards[0].outerHTML.substring(0, 300) : null,
      firstImageSrc: cardImages[0] ? cardImages[0].src : null,
      firstImageNaturalWidth: cardImages[0] ? cardImages[0].naturalWidth : null,
      firstImageComplete: cardImages[0] ? cardImages[0].complete : null,
      gridHTML: document.getElementById('grid').innerHTML.substring(0, 200)
    };
  });
  console.log(JSON.stringify(result, null, 2));
  console.log('\nConsole logs:', logs.length);
  logs.forEach(l => console.log(' ', l));
  console.log('\nPage errors:', errors.length);
  errors.forEach(e => console.log(' ', e));

  await browser.close();
})();