/** 前端侧加载瀑布：找出 2.2s 首屏里剩下的时间花在哪 */
const fs = require('fs');
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW);

const BASE = process.argv[2] || 'http://127.0.0.1:5180';
const HASH = process.argv[3] || '#/p/1/board?ep=1';

(async () => {
  const CAND = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ];
  const browser = await chromium.launch({ headless: true, executablePath: CAND.find((p) => fs.existsSync(p)) });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });

  let total = 0;
  const byType = {};
  const slow = [];
  page.on('response', (res) => {
    const r = res.request();
    const t = r.resourceType();
    byType[t] = (byType[t] || 0) + 1;
    total++;
    const url = res.url().replace(BASE, '');
    if (/\.(js|vue|css|ts)(\?|$)/.test(url) || url.startsWith('/src/') || url.startsWith('/node_modules/')) slow.push(url);
  });

  const t0 = Date.now();
  await page.goto(BASE + '/' + HASH, { waitUntil: 'commit', timeout: 30000 });
  let appearAt = null;
  for (let i = 0; i < 200; i++) {
    const n = await page.evaluate(() => document.querySelectorAll('.el-table__row').length).catch(() => 0);
    if (n > 0) { appearAt = Date.now() - t0; break; }
    await page.waitForTimeout(50);
  }

  const perf = await page.evaluate(() => {
    const res = performance.getEntriesByType('resource');
    const mods = res.filter((x) => /\/node_modules\/|\.vue|element-plus/.test(x.name));
    const parse = [];
    for (const x of res) parse.push({ n: x.name.split('127.0.0.1:5180')[1] || x.name, d: Math.round(x.duration), t: Math.round(x.responseEnd) });
    parse.sort((a, b) => b.d - a.d);
    // 最长的一条模块请求链（responseEnd 最晚）
    parse.sort((a, b) => b.t - a.t);
    return {
      count: res.length,
      transferKB: Math.round(res.reduce((a, x) => a + (x.transferSize || 0), 0) / 1024),
      moduleCount: mods.length,
      moduleMs: Math.round(mods.reduce((a, x) => a + x.duration, 0)),
      slowestByDuration: parse.slice(0, 12),
      latest: parse.slice(0, 12),
      biggestTransfer: res.map((x) => ({ n: x.name.split('127.0.0.1:5180')[1], kb: Math.round((x.transferSize || 0) / 1024) }))
        .sort((a, b) => b.kb - a.kb).slice(0, 10),
    };
  });

  console.log(`首行出现: ${appearAt} ms`);
  console.log(`资源请求总数: ${total}   分类: ${JSON.stringify(byType)}`);
  console.log(`Vite 模块请求(节点数): ${perf.moduleCount}   模块累计耗时: ${perf.moduleMs} ms   传输合计 ${perf.transferKB} KB\n`);
  console.log('— 单条最慢（duration）—');
  for (const x of perf.slowestByDuration) console.log(`  ${String(x.d).padStart(7)} ms  ${String(x.t).padStart(7)} ms 后完成  ${x.n}`);
  console.log('\n— 最后完成的（决定首屏）—');
  for (const x of perf.latest) console.log(`  ${String(x.d).padStart(7)} ms  ${String(x.t).padStart(7)} ms 后完成  ${x.n}`);
  console.log('\n— 传输体积 Top10 —');
  for (const x of perf.biggestTransfer) console.log(`  ${String(x.kb).padStart(6)} KB  ${x.n}`);

  await browser.close();
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
