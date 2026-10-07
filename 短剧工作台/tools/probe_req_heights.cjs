/**
 * 量剧本页「可选参数」行各控件的实际高度/字号，找出不齐的真因。
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

  const rows = await page.evaluate(() => {
    const out = [];
    const push = (name, el) => {
      if (!el) return;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const inner = el.querySelector('input') || el.querySelector('.el-select__wrapper');
      const ir = inner ? inner.getBoundingClientRect() : null;
      const ics = inner ? getComputedStyle(inner) : null;
      out.push({
        name,
        cls: el.className.replace(/\s+/g, ' ').slice(0, 46),
        outer: `${Math.round(r.width)}x${Math.round(r.height)}`,
        top: Math.round(r.top),
        inner: inner ? inner.className.replace(/\s+/g, ' ').slice(0, 34) + ` ${Math.round(ir.width)}x${Math.round(ir.height)}` : '(无)',
        innerFont: ics ? ics.fontSize : '',
        innerPad: ics ? `${ics.paddingTop}/${ics.paddingBottom}` : '',
        innerLine: ics ? ics.lineHeight : '',
        outerFont: cs.fontSize,
      });
    };
    const row = document.querySelector('.req-row');
    push('集数', row.querySelector('.el-input-number'));
    const nums = row.querySelectorAll('.el-input-number');
    push('时长', nums[1]);
    const sel = row.querySelectorAll('.el-select');
    push('题材', sel[0]);
    push('画面风格', sel[1]);
    return { out, rowH: Math.round(row.getBoundingClientRect().height), fs: document.documentElement.getAttribute('data-fs') };
  });
  console.log('字号档 data-fs =', rows.fs, '| 行高 =', rows.rowH);
  for (const r of rows.out) {
    console.log(`${r.name.padEnd(6)} 外框=${r.outer.padEnd(10)} top=${String(r.top).padEnd(5)} 内层=${r.inner.padEnd(40)} 字体=${r.innerFont.padEnd(8)} pad=${r.innerPad.padEnd(12)} lh=${r.innerLine}`);
  }
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
