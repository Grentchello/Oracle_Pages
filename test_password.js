// Test the new password
const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell',
    args: ['--no-sandbox'],
    headless: true,
  });

  const page = await browser.newPage();
  await page.goto('https://grentchello.github.io/Oracle_Pages/tasks/?nocache=' + Date.now(), {waitUntil: 'networkidle2'});

  // Try OLD password (oracle) — should fail
  await page.evaluate(() => {
    document.getElementById('password-input').value = 'oracle';
    document.getElementById('unlock-btn').click();
  });
  await new Promise(r => setTimeout(r, 800));
  const oldPwState = await page.evaluate(() => ({
    errorText: document.getElementById('gate-error').textContent,
    contentVisible: getComputedStyle(document.getElementById('tasks-content')).display !== 'none'
  }));
  console.log('OLD password "oracle":', JSON.stringify(oldPwState));
  console.log('  Expected: errorText="✗ Wrong password", contentVisible=false');

  // Try NEW password
  await page.evaluate(() => {
    document.getElementById('password-input').value = 'aW0^n7qZ^S';
    document.getElementById('unlock-btn').click();
  });
  await new Promise(r => setTimeout(r, 1500));
  const newPwState = await page.evaluate(() => ({
    errorText: document.getElementById('gate-error').textContent,
    contentVisible: getComputedStyle(document.getElementById('tasks-content')).display !== 'none',
    taskTitle: document.querySelector('.task-title')?.textContent
  }));
  console.log('\nNEW password "aW0^n7qZ^S":', JSON.stringify(newPwState));
  console.log('  Expected: contentVisible=true, task="Copy more house keys"');

  await browser.close();
})();