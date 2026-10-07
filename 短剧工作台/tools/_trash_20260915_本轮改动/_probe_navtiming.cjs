/** 精细定位：导航各阶段 + 关键资源传输/解析耗时 */
const fs = require('fs');
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW);

const BASE = process.argv[2] || 'http://127.0.0.1:8770';
const HASH = process.argv[3] || '#/p/1/board?ep=1';

(async () => {
  const CAND = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ];
  const browser = await chromium.launch({ headless: true, executablePath: CAND.find((p) => fs.existsSync(p)) });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });

  const reqs = [];
  page.on('response', async (res) => {
    const url = res.url();
    const r = res.request();
    reqs.push({ url, type: r.resourceType(), status: res.status() });
  });

  await page.goto(BASE + '/' + HASH, { waitUntil: 'load', timeout: 40000 });
  await page.waitForTimeout(2000);

  const out = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0];
    const pick = (o, keys) => Object.fromEntries(keys.map((k) => [k, Math.round(o[k] || 0)]));
    const scales = ['startTime', 'redirectStart', 'redirectEnd', 'fetchStart', 'domainLookupStart',
      'domainLookupEnd', 'connectStart', 'connectEnd', 'requestStart', 'responseStart',
      'responseEnd', 'domInteractive', 'domContentLoadedEventStart', 'domContentLoadedEventEnd',
      'domComplete', 'loadEventStart', 'loadEventEnd'];
    const res = performance.getEntriesByType('resource').map((x) => ({
      n: x.name.replace(location.origin, '') || '(doc)',
      type: x.initiatorType,
      start: Math.round(x.startTime),
      reqS: Math.round(x.requestStart),
      resS: Math.round(x.responseStart),
      resE: Math.round(x.responseEnd),
      dur: Math.round(x.duration),
      transfer: x.transferSize,
      decoded: x.decodedBodySize,
      ttfb: Math.round(x.responseStart - x.requestStart),
      body: Math.round(x.responseEnd - x.responseStart),
    })).sort((a, b) => b.resE - a.resE).slice(0, 16);
    return { nav: pick(nav, scales), res };
  });

  console.log('=== 导航阶段（ms） ===');
  for (const [k, v] of Object.entries(out.nav)) console.log(`  ${k.padEnd(26)} ${v}`);
  console.log('\n=== 最后完成的资源（按 responseEnd 倒序，前 16）===');
  console.log('  start    ttfb   body    resEnd  transfer  decoded  资源');
  for (const x of out.res) {
    console.log(`  ${String(x.start).padStart(6)} ${String(x.ttfb).padStart(6)} ${String(x.body).padStart(6)} ${String(x.resE).padStart(8)} ${String((x.transfer / 1024).toFixed(0)).padStart(8)}KB ${String((x.decoded / 1024).toFixed(0)).padStart(8)}KB  ${x.n}`);
  }

  await browser.close();
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
