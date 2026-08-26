// Real browser test for tasks feature
const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    headless: true,
  });

  const page = await browser.newPage();
  const errors = [];
  const logs = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));
  page.on('pageerror', err => errors.push(err.message));
  page.on('requestfailed', req => console.log('Failed request:', req.url()));
  page.on('response', resp => {
    if (resp.status() >= 400) console.log(`HTTP ${resp.status()}: ${resp.url()}`);
  });

  // Test 1: Tasks page (gated)
  console.log('Loading tasks page...');
  await page.goto('https://grentchello.github.io/Oracle_Pages/tasks/?nocache=' + Date.now(), {waitUntil: 'networkidle2', timeout: 30000});

  // Should see the gate initially
  const gateVisible = await page.evaluate(() => {
    const gate = document.getElementById('tasks-gate');
    return gate && getComputedStyle(gate).display !== 'none';
  });
  console.log('Gate visible (should be true):', gateVisible);

  // Try wrong password
  await page.evaluate(() => {
    document.getElementById('password-input').value = 'wrong';
    document.getElementById('unlock-btn').click();
  });
  await new Promise(r => setTimeout(r, 1500));
  const wrongPwState = await page.evaluate(() => {
    return {
      gateVisible: document.getElementById('tasks-gate').style.display !== 'none',
      errorText: document.getElementById('gate-error').textContent,
      inputValue: document.getElementById('password-input').value
    };
  });
  console.log('After wrong password:', JSON.stringify(wrongPwState));

  // Try correct password
  await page.evaluate(() => {
    document.getElementById('password-input').value = 'oracle';
    document.getElementById('unlock-btn').click();
  });
  await new Promise(r => setTimeout(r, 1000));
  const contentVisible = await page.evaluate(() => {
    const content = document.getElementById('tasks-content');
    return content && getComputedStyle(content).display !== 'none';
  });
  console.log('Content visible after correct password (should be true):', contentVisible);

  // Check the actual task is rendered
  const taskText = await page.evaluate(() => {
    const items = document.querySelectorAll('.task-title');
    return Array.from(items).map(e => e.textContent);
  });
  console.log('Task titles shown:', JSON.stringify(taskText));

  // Test 2: Master dashboard link
  console.log('\nLoading master dashboard...');
  await page.goto('https://grentchello.github.io/Oracle_Pages/?nocache=' + Date.now(), {waitUntil: 'networkidle2', timeout: 30000});
  const hasTasksLink = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('a')).some(a => a.href.includes('tasks/'));
  });
  console.log('Master dashboard has tasks link (should be true):', hasTasksLink);

  console.log('\n=== CONSOLE LOGS ===');
  logs.forEach(l => console.log(l));
  console.log('\n=== PAGE ERRORS ===');
  if (errors.length === 0) console.log('(none)');
  else errors.forEach(e => console.log(e));

  await browser.close();
})();