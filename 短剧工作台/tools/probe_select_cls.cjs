/**
 * 抓 el-select 的 small 尺寸真实类名与写死值，确定覆盖选择器。
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
    const sel = row.querySelector('.el-select');
    const wrap = sel.querySelector('.el-select__wrapper');
    const num = row.querySelector('.el-input-number');
    const numInner = num.querySelector('.el-input__inner');
    const cs = (el) => {
      const c = getComputedStyle(el);
      return {
        cls: el.className,
        h: Math.round(el.getBoundingClientRect().height),
        minH: c.minHeight,
        fs: c.fontSize,
        pad: c.padding,
      };
    };
    const root = getComputedStyle(document.documentElement);
    return {
      wrap: cs(wrap),
      selOuter: cs(sel),
      numOuter: cs(num),
      numInner: cs(numInner),
      vars: {
        ctl: root.getPropertyValue('--ui-ctl').trim(),
        ctlSm: root.getPropertyValue('--ui-ctl-sm').trim(),
        elSizeSm: root.getPropertyValue('--el-component-size-small').trim(),
        elFontSm: root.getPropertyValue('--el-font-size-small').trim(),
        elFontXs: root.getPropertyValue('--el-font-size-extra-small').trim(),
      },
    };
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
