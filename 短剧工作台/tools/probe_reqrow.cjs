/**
 * 剧本页参数行默认值巡检：不填任何东西，读每个控件的实际值与 placeholder。
 */
const fs = require('fs');
const PW_CORE = process.env.PW_CORE
  || 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW_CORE);
const BASE = process.env.BASE || 'http://127.0.0.1:5192';
const EXE = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find((p) => fs.existsSync(p));

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: EXE });
  const page = await (await browser.newContext({ viewport: { width: 1600, height: 950 } })).newPage();
  await page.goto(`${BASE}/?_r=${Date.now()}/#/p/1/script`, { waitUntil: 'load', timeout: 25000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1200);

  const info = await page.evaluate(() => {
    const row = document.querySelector('.req-row');
    if (!row) return { err: '没找到 .req-row' };
    const cells = [...row.children].map((el) => {
      const inp = el.matches('input') ? el : el.querySelector('input');
      const txt = (el.innerText || '').trim();
      if (inp) {
        return {
          tag: el.className.split(' ')[0],
          value: inp.value,
          placeholder: inp.getAttribute('placeholder') || '',
          readOnly: inp.readOnly,
        };
      }
      return { tag: el.className.split(' ')[0], text: txt };
    });
    return { cells };
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
