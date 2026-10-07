/**
 * 字号档位探测：在 4 个档位下分别量出关键元素的真实字号，
 * 并检查有没有因为字变大而出现横向溢出、表格被压扁。
 * 用法：node tools/probe_font.cjs [baseUrl]
 */
const fs = require('fs');
const PW_CORE = process.env.PW_CORE
  || 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW_CORE);

const BASE = process.argv[2] || 'http://127.0.0.1:5192';
const OUT = 'D:/Aicomfyui/短剧工作台/storage/ui-tour';
const FS = ['compact', 'normal', 'large', 'xlarge'];

const CANDIDATES = [
  process.env.CHROME_EXE,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].filter(Boolean);
const EXE = CANDIDATES.find((p) => fs.existsSync(p));
if (!EXE) throw new Error('找不到可用浏览器');

const MEASURE = () => {
  const g = (sel) => {
    const el = document.querySelector(sel);
    return el ? getComputedStyle(el).fontSize : null;
  };
  const box = (sel) => {
    const el = document.querySelector(sel);
    return el ? { w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height) } : null;
  };
  const bw = document.querySelector('.el-table__body-wrapper');
  const rows = [...document.querySelectorAll('.el-table__body tbody tr')];
  const rowH = rows.length ? Math.round(rows[0].getBoundingClientRect().height) : 0;
  return {
    fs: document.documentElement.dataset.fs,
    body: getComputedStyle(document.body).fontSize,
    nav: g('.side a'),
    pageTitle: g('.top h2'),
    cardTitle: g('.card > h3'),
    tableHead: g('.el-table th .cell'),
    tableCell: g('.el-table td .cell'),
    btnSmall: g('.el-button--small'),
    pill: g('.pill'),
    slotIdx: g('.slot .idx'),
    // 溢出检查
    pageOverflowX: document.documentElement.scrollWidth - window.innerWidth,
    tableOverflowX: bw ? bw.scrollWidth - bw.clientWidth : null,
    // 信息密度
    rowH,
    rows,
    rowsPerScreen: rowH ? Math.floor((window.innerHeight - 230) / rowH) : null,
    sidebarW: box('.side')?.w,
    topH: box('.top')?.h,
  };
};

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: EXE });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const page = await ctx.newPage();

  const out = [];
  for (const v of FS) {
    await page.goto(BASE + '/', { waitUntil: 'load', timeout: 25000 });
    await page.evaluate((x) => localStorage.setItem('studio.fontScale', x), v);
    await page.goto(BASE + '/#/p/1/board', { waitUntil: 'load', timeout: 25000 });
    await page.evaluate((x) => { document.documentElement.dataset.fs = x; }, v);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(600);
    const m = await page.evaluate(MEASURE);
    m.rows = m.rows.length;
    out.push(m);
  }

  // ---------- 交互验证：顶栏「Aa」切档 + 持久化 ----------
  const p2 = await ctx.newPage();
  await p2.goto(BASE + '/', { waitUntil: 'load', timeout: 25000 });
  await p2.evaluate(() => localStorage.removeItem('studio.fontScale'));
  await p2.reload({ waitUntil: 'load', timeout: 25000 });   // 清掉记忆后重载 = 全新用户视角
  await p2.waitForTimeout(700);

  const snap = () => p2.evaluate(() => ({
    fs: document.documentElement.dataset.fs,
    body: getComputedStyle(document.body).fontSize,
    label: [...document.querySelectorAll('.top button')]
      .find((x) => /Aa/.test(x.innerText))?.innerText.replace(/\s+/g, ' ').trim() || '(未找到按钮)',
    saved: localStorage.getItem('studio.fontScale'),
  }));
  const fresh = await snap();
  await p2.screenshot({ path: OUT + '/font_default_assets.png' });

  // 真的用鼠标点开下拉，再点「特大」
  await p2.locator('.top button:has-text("Aa")').click();
  await p2.waitForTimeout(400);
  const menu = await p2.evaluate(() =>
    [...document.querySelectorAll('.el-dropdown-menu__item')].map((x) => x.innerText.replace(/\s+/g, ' ').trim()),
  );
  const menuShot = OUT + '/font_menu.png';
  await p2.screenshot({ path: menuShot });
  await p2.locator('.el-dropdown-menu__item:has-text("特大")').click();
  await p2.waitForTimeout(500);
  const picked = await snap();

  // 刷新后是否记得
  await p2.reload({ waitUntil: 'load', timeout: 25000 });
  await p2.waitForTimeout(900);
  const persisted = await snap();

  await p2.goto(BASE + '/#/p/1/board', { waitUntil: 'load', timeout: 25000 });
  await p2.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await p2.waitForTimeout(600);
  await p2.screenshot({ path: OUT + '/font_xlarge_board.png' });

  await browser.close();

  const pad = (s, n) => String(s ?? '-').padEnd(n);
  console.log('\n档位'.padEnd(12) + '正文'.padEnd(9) + '导航'.padEnd(9) + '表格'.padEnd(9) + '表头'.padEnd(9) + 'small钮'.padEnd(10) + 'pill'.padEnd(9) + '行高'.padEnd(7) + '一屏行'.padEnd(8) + '侧栏'.padEnd(7) + '横向溢出');
  console.log('-'.repeat(108));
  for (const m of out) {
    console.log(
      pad(m.fs, 12) + pad(m.body, 9) + pad(m.nav, 9) + pad(m.tableCell, 9) + pad(m.tableHead, 9)
      + pad(m.btnSmall, 10) + pad(m.pill, 9) + pad(m.rowH + 'px', 7)
      + pad(m.rowsPerScreen, 8) + pad(m.sidebarW + 'px', 7)
      + `页面${m.pageOverflowX} / 表格${m.tableOverflowX}`,
    );
  }
  console.log(`\n表格总行数: ${out[2].rows}`);
  console.log('\n================ 顶栏切档交互 ================');
  console.log(`  首次访问（无记忆）  data-fs=${fresh.fs}  正文=${fresh.body}  按钮「${fresh.label}」`);
  console.log(`  下拉可选档位        ${menu.join(' | ')}`);
  console.log(`  点「特大」之后      data-fs=${picked.fs}  正文=${picked.body}  按钮「${picked.label}」  存入记忆=${picked.saved}`);
  console.log(`  刷新后              data-fs=${persisted.fs}  正文=${persisted.body}  按钮「${persisted.label}」`);
  const ok = fresh.fs === 'large' && picked.fs === 'xlarge' && persisted.fs === 'xlarge'
    && picked.body === '18px' && /特大/.test(picked.label);
  console.log(ok ? '  ✓ 默认档 / 切换 / 持久化 全部正常' : '  !! 有异常，请看上面三行');
  console.log(`截图: ${OUT}/font_default_assets.png / font_menu.png / font_xlarge_board.png`);
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
