/**
 * 端到端验证：镜头90 注入后，正文里的「镜头语言句」是否可点、点击是否弹窗。
 * 用法：node tools/_e2e_wizlink.cjs
 */
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW);
const BASE = 'http://127.0.0.1:5180';
const EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = 'D:/Aicomfyui/短剧工作台/storage/ui-tour';

(async () => {
  const b = await chromium.launch({ headless: true, executablePath: EXE });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 950 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 160)));

  await p.goto(BASE + '/?_r=' + Date.now() + '#/p/1/shot/90', { waitUntil: 'load' });
  await p.waitForTimeout(2600);

  const st = await p.evaluate(() => {
    const links = [...document.querySelectorAll('.wiz-link')];
    return {
      title: (document.querySelector('.shot-title') || {}).innerText || null,
      count: links.length,
      texts: links.map((x) => x.innerText.trim()),
      styles: links.map((x) => {
        const s = getComputedStyle(x);
        return { color: s.color, deco: s.textDecorationLine, cursor: s.cursor };
      }),
      around: links.map((x) => (x.parentElement.innerText || '').slice(0, 90)),
    };
  });
  console.log('镜头90 详情页');
  console.log('  标题:', st.title);
  console.log('  可点句数量:', st.count);
  st.texts.forEach((t, i) => {
    console.log(`   [${i}] ${JSON.stringify(t)}`);
    console.log(`        样式: ${JSON.stringify(st.styles[i])}`);
    console.log(`        上下文: ${JSON.stringify(st.around[i])}`);
  });
  await p.screenshot({ path: OUT + '/e2e_wizlink.png', fullPage: false });

  // 点第一处可点句
  if (st.count) {
    const link = p.locator('.wiz-link').first();
    await link.click();
    await p.waitForTimeout(1000);
    const dlg = await p.evaluate(() => {
      const d = [...document.querySelectorAll('.el-dialog')].find((x) => x.getBoundingClientRect().width > 0);
      if (!d) return null;
      const vals = [...d.querySelectorAll('.el-select')].map((s) => s.innerText.trim().replace(/\s+/g, ' '));
      const chosen = [...d.querySelectorAll('.pos-cell.is-on, .pos-cell.active, .pos-cell.on')].map((c) => c.innerText.trim());
      return {
        title: d.querySelector('.el-dialog__title')?.innerText,
        selects: vals,
        chosenCells: chosen,
        actions: [...d.querySelectorAll('.actions button')].map((x) => x.innerText.trim()),
      };
    });
    console.log('\n  点这句 → 弹窗:', JSON.stringify(dlg, null, 1));
    await p.screenshot({ path: OUT + '/e2e_wizlink_dlg.png' });

    // 关掉，再验证工具栏入口也还能用
    await p.keyboard.press('Escape');
    await p.waitForTimeout(700);
    const btn = p.locator('.pe-head button', { hasText: '镜头设置' }).first();
    if (await btn.count()) {
      await btn.click();
      await p.waitForTimeout(900);
      const t2 = await p.evaluate(() => {
        const d = [...document.querySelectorAll('.el-dialog')].find((x) => x.getBoundingClientRect().width > 0);
        return d ? d.querySelector('.el-dialog__title')?.innerText : null;
      });
      console.log('  工具栏「镜头设置」→ 弹窗:', t2);
    } else {
      console.log('  !! 工具栏入口没找到');
    }
  } else {
    console.log('  !! 没有可点句（注入未生效？）');
  }

  console.log('\n  控制台:', errs.length ? errs : '无');
  await b.close();
})();
