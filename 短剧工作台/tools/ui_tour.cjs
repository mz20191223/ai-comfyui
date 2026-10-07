/**
 * 前端页面巡检：逐个路由打开，抓 console 错误 / 未捕获异常 / 失败请求，并截图。
 * 用法：node tools/ui_tour.cjs [baseUrl] [outDir]
 */
const path = require('path');
const fs = require('fs');

const PW_CORE = process.env.PW_CORE
  || 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW_CORE);

const BASE = process.argv[2] || 'http://127.0.0.1:5192';
const OUT = process.argv[3] || 'D:/Aicomfyui/短剧工作台/storage/ui-tour';

const ROUTES = [
  ['项目列表', '#/'],
  ['任务中心', '#/tasks'],
  ['接口配置', '#/settings'],
  ['剧本', '#/p/1/script'],
  ['镜头看板', '#/p/1/board'],
  ['镜头详情', '#/p/1/shot/__SHOT__'],
  ['资产库', '#/p/1/assets'],
  ['健康巡检', '#/p/1/health'],
  ['提示词中心', '#/p/1/prompts'],
  ['创作流水线', '#/p/1/create'],
  ['时间轴合成', '#/p/1/timeline'],
];

// 与业务无关的噪音，不计入问题
const IGNORE = [
  /favicon/i,
  /ResizeObserver loop/i,
  /Download the Vue Devtools/i,
  /\[vite\] connect/i,
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });

  // 镜头 id 会随重建库变化，不能写死；从接口取一个真实存在的
  let shotId = 1;
  try {
    const res = await fetch(`${BASE}/api/episodes/1/shots`);
    const list = await res.json();
    const arr = Array.isArray(list) ? list : list.shots || list.items || [];
    if (arr.length) shotId = arr[0].id ?? arr[0].shot_id ?? shotId;
  } catch (e) {
    console.log('取镜头 id 失败，回退 1:', e.message);
  }
  console.log('使用镜头 id:', shotId);
  // ms-playwright 里的 chromium 在本机报 0xC000007B（二进制跑不起来），改用系统浏览器。
  const CANDIDATES = [
    process.env.CHROME_EXE,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ].filter(Boolean);
  const EXE = CANDIDATES.find((p) => fs.existsSync(p));
  if (!EXE) throw new Error('找不到可用浏览器，请设置 CHROME_EXE 环境变量');
  console.log('使用浏览器:', EXE);
  const browser = await chromium.launch({ headless: true, executablePath: EXE });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 } });
  const report = [];
  let nav = [];

  for (const [name, rawHash] of ROUTES) {
    const hash = rawHash.replace('__SHOT__', String(shotId));
    const page = await ctx.newPage();
    const errors = [];
    const warnings = [];
    const failed = [];

    page.on('console', (m) => {
      const t = m.text();
      if (IGNORE.some((r) => r.test(t))) return;
      if (m.type() === 'error') errors.push(t);
      else if (m.type() === 'warning') warnings.push(t);
    });
    page.on('pageerror', (e) => errors.push('UNCAUGHT: ' + (e.message || String(e))));
    page.on('requestfailed', (r) => {
      const u = r.url();
      if (IGNORE.some((x) => x.test(u))) return;
      failed.push(`${r.failure()?.errorText || '?'} ${u.slice(0, 120)}`);
    });
    // 记录 4xx/5xx 资源（含接口与非接口）
    const badApi = [];
    page.on('response', (res) => {
      const st = res.status();
      if (st < 400) return;
      const u = res.url();
      if (IGNORE.some((x) => x.test(u))) return;
      badApi.push(`${st} ${u.replace(BASE, '').slice(0, 110)}`);
    });

    let textLen = 0;
    let shot = '';
    try {
      await page.goto(BASE + '/' + hash, { waitUntil: 'load', timeout: 25000 });
      // 固定延迟不可靠：镜头看板要等 projects→episodes→health→shots→N 个缩略图，
      // 实测 1.5s 时还是空表、2.5s 才出 34 行。改成等网络静默 + 少量兜底。
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(900);
      textLen = (await page.evaluate(() => document.body.innerText || '')).trim().length;
      // 侧边栏「当前项目」分组只在带 pid 的页面渲染，所以要在项目内页面抓
      if (!nav.length && hash.includes('/p/')) {
        nav = await page.evaluate(() =>
          [...document.querySelectorAll('.side a')].map((a) =>
            a.textContent.trim().replace(/\s+/g, ' ')
          )
        );
      }
      const fname = `tour_${String(report.length + 1).padStart(2, '0')}_${name}.png`;
      shot = path.join(OUT, fname);
      await page.screenshot({ path: shot, fullPage: false });
    } catch (e) {
      errors.push('NAV: ' + (e.message || String(e)).split('\n')[0]);
    }

    report.push({
      name, hash,
      textLen,
      nav,
      errors: [...new Set(errors)].slice(0, 6),
      warnings: [...new Set(warnings)].slice(0, 3),
      failed: [...new Set(failed)].slice(0, 4),
      badApi: [...new Set(badApi)].slice(0, 8),
      shot: shot ? path.basename(shot) : '',
    });
    await page.close();
  }

  await browser.close();

  // 控制台输出
  console.log('\n================ 侧边导航项 ================');
  nav.forEach((t, i) => console.log(`  ${i + 1}. ${t}`));
  const wanted = ['镜头看板', '资产库', '提示词中心', '健康报告', '时间轴与合成', '创作流水线'];
  const missing = wanted.filter((w) => !nav.some((t) => t.includes(w)));
  console.log(missing.length ? `  !! 导航缺少: ${missing.join('、')}` : '  导航齐全');

  console.log('\n================ 巡检结果 ================');
  let bad = 0;
  for (const r of report) {
    const n = r.errors.length + r.failed.length + r.badApi.length + (r.textLen < 30 ? 1 : 0);
    if (n) bad++;
    console.log(`\n[${r.textLen < 30 ? '空页' : '有内容'}] ${r.name}  (${r.hash})  文本${r.textLen}字`);
    if (r.textLen < 30) console.log('   !! 页面几乎没有内容，疑似白屏');
    r.errors.forEach((e) => console.log('   ERR  ' + e.slice(0, 220)));
    r.badApi.forEach((e) => console.log('   HTTP ' + e));
    r.failed.forEach((e) => console.log('   NET  ' + e.slice(0, 160)));
    if (r.warnings.length) console.log('   warn ' + r.warnings.join(' | ').slice(0, 160));
  }
  console.log(`\n合计 ${report.length} 页，其中 ${bad} 页有问题。截图目录：${OUT}`);

  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2), 'utf8');
  process.exit(0);
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
