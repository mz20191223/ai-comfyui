const fs = require('fs');
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW);
const BASE = 'http://127.0.0.1:5192';
const EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = 'D:/Aicomfyui/短剧工作台/storage/ui-tour';

(async () => {
  const b = await chromium.launch({ headless: true, executablePath: EXE });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 200)));

  await p.goto(BASE + '/#/settings', { waitUntil: 'load', timeout: 25000 });
  await p.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await p.waitForFunction(
    () => document.querySelectorAll('.el-table__body tbody tr').length > 0,
    { timeout: 15000 },
  ).catch(() => {});
  await p.waitForTimeout(800);

  const summary = await p.evaluate(() => {
    const rows = [...document.querySelectorAll('.el-table__body tbody tr')];
    const providerRows = rows.map((r) => (r.innerText || '').replace(/\s+/g, ' ').trim()).filter((t) => t.length);
    return {
      title: document.title,
      tables: document.querySelectorAll('.el-table').length,
      providerRows: providerRows.slice(0, 6),
      hasPoolCol: (document.body.innerText || '').includes('账号池'),
    };
  });
  console.log('设置页：表格', summary.tables, '| 有账号池列:', summary.hasPoolCol);
  summary.providerRows.forEach((t) => console.log('   ', t.slice(0, 150)));

  await p.screenshot({ path: OUT + '/settings_providers.png' });

  // 打开多账号的那个供应商（ListenHub，账号数 > 1）
  const opened = await p.evaluate(() => {
    const btns = [...document.querySelectorAll('.el-button')].filter((x) => /^账号/.test((x.innerText || '').trim()));
    if (!btns.length) return false;
    const multi = btns.find((x) => {
      const m = (x.innerText || '').match(/\((\d+)\)/);
      return m && Number(m[1]) > 1;
    });
    const target = multi || btns[0];
    target.click();
    return (target.innerText || '').trim();
  });
  console.log('点击账号按钮:', opened);
  await p.waitForTimeout(1200);

  const dlg = await p.evaluate(() => {
    const d = [...document.querySelectorAll('.el-dialog')].filter((x) => x.offsetParent !== null).pop();
    if (!d) return null;
    return {
      title: (d.querySelector('.el-dialog__title')?.innerText || '').trim(),
      rows: [...d.querySelectorAll('.el-table__body tbody tr')].map((r) => (r.innerText || '').replace(/\s+/g, ' ').trim()),
      buttons: [...d.querySelectorAll('.el-button')].map((x) => (x.innerText || '').trim()).filter(Boolean),
    };
  });
  if (dlg) {
    console.log('\n弹窗:', dlg.title);
    console.log('  列按钮:', dlg.buttons.join(' / '));
    console.log('  账号行数:', dlg.rows.length);
    dlg.rows.forEach((t) => console.log('   ', t.slice(0, 170)));
    await p.screenshot({ path: OUT + '/settings_credpool.png' });
  } else {
    console.log('!! 弹窗未打开');
  }

  console.log('\n控制台错误:', errs.length ? errs.slice(0, 5).join(' | ') : '无');
  await b.close();
})();
