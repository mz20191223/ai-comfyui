/**
 * 操作列按钮「单行不换行」巡检。
 * 在 4 个字号档下遍历所有含表格的页面，检查每张表「操作」列：
 *   - 按钮是否同一行（top 值唯一）
 *   - 容器是否横向溢出（被裁剪）
 *   - 行高是否被撑成两倍
 * 用法：node tools/probe_oprow.cjs [baseUrl]
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

const PAGES = [
  ['项目列表', '/#/'],
  ['剧本', '/#/p/1/script'],
  ['分镜看板', '/#/p/1/board'],
  ['创作台', '/#/p/1/create'],
  ['资产库', '/#/p/1/assets'],
  ['健康报告', '/#/p/1/health'],
  ['时间轴', '/#/p/1/timeline'],
  ['提示词中心', '/#/p/1/prompts'],
  ['接口与设置', '/#/settings'],
  ['任务中心', '/#/tasks'],
];

const MEASURE = () => {
  const out = [];
  document.querySelectorAll('.el-table').forEach((tbl, ti) => {
    const cells = [...tbl.querySelectorAll('td .cell')].filter((c) => c.querySelector('.op-row'));
    if (!cells.length) return;
    const kinds = new Set();
    cells.forEach((cell) => {
      const row = cell.querySelector('.op-row');
      const btns = [...row.querySelectorAll('.el-button')];
      const top = new Set(btns.map((b) => Math.round(b.getBoundingClientRect().top)));
      const r = row.getBoundingClientRect();
      kinds.add(JSON.stringify({
        n: btns.length,
        lines: top.size,
        need: Math.ceil(row.scrollWidth),
        have: Math.ceil(cell.clientWidth),
        rowH: Math.round(r.height),
      }));
    });
    [...kinds].forEach((k) => out.push({ table: ti, ...JSON.parse(k), sample: cells.length }));
  });
  return {
    list: out,
    tables: document.querySelectorAll('.el-table').length,
    rowsTotal: document.querySelectorAll('.el-table__body tbody tr').length,
    text: (document.querySelector('.body')?.innerText || '').replace(/\s+/g, ' ').slice(0, 70),
    // 完整内文长度（用于区分「真白屏」与「该页本就是卡片/表单布局」）
    textLen: (document.querySelector('.body')?.innerText || '').replace(/\s+/g, ' ').trim().length,
    cards: document.querySelectorAll('.card, .a-card, .grid, .asset-card').length,
  };
};

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: EXE });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const page = await ctx.newPage();
  const rows = [];
  const miss = [];
  const skipped = [];
  const shots = [];

  for (const v of FS) {
    await page.goto(BASE + '/', { waitUntil: 'load', timeout: 25000 });
    await page.evaluate((x) => localStorage.setItem('studio.fontScale', x), v);

    for (const [label, path] of PAGES) {
      // hash 内跳转是同文档导航，DOM 可能还是上一页的残留；
      // 加个一次性查询串强制整页重载，让 Vue 从路由初始状态直接落到目标页。
      const url = `${BASE}/?_r=${Date.now()}${path}`;
      await page.goto(url, { waitUntil: 'load', timeout: 25000 });
      await page.evaluate((x) => { document.documentElement.dataset.fs = x; }, v);
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      // 表格数据是异步拉的，必须等出行（或空状态）再量，否则会量到 loading 骨架
      await page.waitForFunction(
        () => document.querySelectorAll('.el-table__body tbody tr').length > 0
          || document.querySelector('.el-table__empty-block'),
        { timeout: 12000 },
      ).catch(() => {});
      await page.waitForTimeout(600);

      // 提示词中心是多 tab 结构，逐个切过去把表都亮出来
      const tabs = await page.locator('.el-tabs__item').count();
      const passes = tabs > 1 ? tabs : 1;
      for (let i = 0; i < passes; i++) {
        if (tabs > 1) {
          await page.locator('.el-tabs__item').nth(i).click();
          await page.waitForFunction(
            () => document.querySelectorAll('.el-table__body tbody tr').length > 0
              || document.querySelector('.el-table__empty-block'),
            { timeout: 10000 },
          ).catch(() => {});
          await page.waitForTimeout(400);
        }
        const m = await page.evaluate(MEASURE);
        const tag = tabs > 1 ? `${label}#tab${i + 1}` : label;
        // 只有「页面根本没渲染出表格」才算漏探；本来就没有操作列的页面不算。
        // 另需区分两类：① 整页白屏/报错（内文极短）→ 真漏探；② 该页本就是卡片/表单布局
        // （如资产库是卡片网格，没有 el-table）→ 正常，移到 skipped 不算异常。
        if (!m.list.length && m.tables === 0) {
          const item = {
            fs: v, page: tag, tables: m.tables, rows: m.rowsTotal,
            textLen: m.textLen, cards: m.cards, text: m.text,
          };
          // 内文够长（或有卡片容器）说明页面渲染出来了，只是不含 el-table
          if (m.textLen >= 150 || m.cards > 0) skipped.push(item); else miss.push(item);
        }
        m.list.forEach((r) => rows.push({ fs: v, page: tag, ...r }));
      }

      if (v === 'xlarge' && path === '/#/projects') {
        await page.screenshot({ path: OUT + '/oprow_projects.png' });
        shots.push('oprow_projects.png');
      }
      if (v === 'xlarge' && path === '/#/p/1/creation') {
        await page.screenshot({ path: OUT + '/oprow_creation.png' });
        shots.push('oprow_creation.png');
      }
    }
  }

  await browser.close();

  console.log('\n档位'.padEnd(10) + '页面'.padEnd(18) + '表'.padEnd(4) + '按钮数'.padEnd(8) + '行数'.padEnd(6) + '需宽'.padEnd(7) + '可用'.padEnd(7) + '判定');
  console.log('-'.repeat(84));
  let bad = 0;
  for (const r of rows) {
    const ok = r.lines === 1 && r.need <= r.have;
    if (!ok) bad++;
    console.log(
      r.fs.padEnd(10) + r.page.padEnd(18) + String(r.table).padEnd(4)
      + String(r.n).padEnd(8) + String(r.lines).padEnd(6)
      + String(r.need).padEnd(7) + String(r.have).padEnd(7)
      + (ok ? '✓ 一行' : (r.lines > 1 ? '✗ 换行' : '✗ 溢出')),
    );
  }
  console.log(`\n共检查 ${rows.length} 处操作列，异常 ${bad} 处。`);
  if (miss.length) {
    console.log('\n以下页面疑似白屏/报错（内文过短，需人工确认）：');
    miss.forEach((m) => console.log(`  ${m.fs} ${m.page} · 表格${m.tables}个 · 行${m.rows}条 · 正文「${m.text}」`));
  }
  if (skipped.length) {
    const byPage = new Map();
    skipped.forEach((s) => { if (!byPage.has(s.page)) byPage.set(s.page, s); });
    console.log('\n以下页面非表格布局，本就不含 el-table，已跳过（不算异常）：');
    byPage.forEach((s, page) => console.log(
      `  ${page} · 内文${s.textLen}字 · 卡片容器${s.cards}个 · 「${s.text}…」`,
    ));
  }
  console.log(`截图: ${shots.map((s) => OUT + '/' + s).join(' / ')}`);
  process.exit(bad || miss.length ? 2 : 0);
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
