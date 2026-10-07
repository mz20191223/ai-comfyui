/**
 * 量「新建项目」对话框里默认尺寸的 input / select / button 高度，看是否也不齐。
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
  await page.goto(`${BASE}/?_r=${Date.now()}/#/`, { waitUntil: 'load', timeout: 25000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1000);
  await page.getByRole('button', { name: /新建项目/ }).first().click();
  await page.waitForTimeout(800);

  const info = await page.evaluate(() => {
    const dlg = document.querySelector('.el-dialog');
    const grab = (sel, name) => {
      const el = dlg.querySelector(sel);
      if (!el) return { name, miss: true };
      const r = el.getBoundingClientRect();
      return {
        name,
        cls: el.className.replace(/\s+/g, ' ').slice(0, 40),
        h: Math.round(r.height),
        w: Math.round(r.width),
        fs: getComputedStyle(el).fontSize,
      };
    };
    const wrap = dlg.querySelector('.el-select__wrapper');
    return {
      items: [
        grab('.el-input__wrapper', 'input(输入框)'),
        grab('.el-select__wrapper', 'select wrapper'),
        grab('.el-input-number', 'input-number'),
      ],
      wrapMinH: wrap ? getComputedStyle(wrap).minHeight : '',
      wrapFont: wrap ? getComputedStyle(wrap).fontSize : '',
    };
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
