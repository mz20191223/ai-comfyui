/** 验证 1.6s 前置延迟是不是「代理解析/自动探测」造成 */
const fs = require('fs');
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW);

const EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe';

const CASES = [
  { name: '① 默认（复现现状）', args: [] },
  { name: '② 关代理 --no-proxy-server', args: ['--no-proxy-server'] },
  { name: '③ 直连 + 不探测 --proxy-server=direct://', args: ['--proxy-server=direct://', '--proxy-bypass-list=*'] },
  { name: '④ 关 IPv6/host 解析规则', args: ['--no-proxy-server', '--host-resolver-rules=MAP localhost 127.0.0.1'] },
];

(async () => {
  for (const c of CASES) {
    const browser = await chromium.launch({ headless: true, executablePath: EXE, args: c.args });
    const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
    await page.goto('http://127.0.0.1:8770/#/p/1/board?ep=1', { waitUntil: 'load', timeout: 40000 });
    let firstRow = null;
    const t0 = Date.now();
    for (let i = 0; i < 200; i++) {
      const n = await page.evaluate(() => document.querySelectorAll('.el-table__row').length).catch(() => 0);
      if (n > 0) { firstRow = Date.now() - t0; break; }
      await page.waitForTimeout(30);
    }
    const nav = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0];
      const g = (k) => Math.round(n[k] || 0);
      return { fetchStart: g('fetchStart'), dnsStart: g('domainLookupStart'), dnsEnd: g('domainLookupEnd'),
        connectStart: g('connectStart'), requestStart: g('requestStart'), responseStart: g('responseStart'),
        dcl: g('domContentLoadedEventEnd'), load: g('loadEventEnd') };
    });
    const gap = nav.dnsStart - nav.fetchStart;
    console.log(`\n${c.name}`);
    console.log(`  加载前排队/解析: ${gap} ms    文档 TTFB: ${nav.responseStart - nav.requestStart} ms`);
    console.log(`  DCL ${nav.dcl} ms   load ${nav.load} ms   表格首行(含轮询) ${firstRow} ms`);
    await browser.close();
  }
})().catch((e) => { console.error('FATAL', e.message); process.exit(1); });
