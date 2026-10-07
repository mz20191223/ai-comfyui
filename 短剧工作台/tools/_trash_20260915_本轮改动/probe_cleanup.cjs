/**
 * 验收本轮改动：看板出图/出视频两列、详情页单列布局、镜头设置改弹窗、片段库已删。
 * 用法：node tools/probe_cleanup.cjs
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
  let errs = [];
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 150)); });
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 150)));
  p.on('response', (r) => { if (r.status() >= 400) errs.push(`HTTP${r.status()} ${r.url().slice(0, 70)}`); });

  console.log('══════ 看板 ══════');
  await p.goto(BASE + '/?_r=' + Date.now() + '#/p/1/board?ep=1', { waitUntil: 'load' });
  await p.waitForTimeout(2600);
  const board = await p.evaluate(() => ({
    heads: [...document.querySelectorAll('.el-table__header th')].map((t) => t.innerText.trim().replace(/\s+/g, '')),
    rows: document.querySelectorAll('.el-table__body tr').length,
    pills: [...document.querySelectorAll('.el-table__body .pill')].slice(0, 6).map((x) => x.innerText.trim()),
  }));
  console.log('  表头:', board.heads.join(' | '));
  console.log('  行数:', board.rows);
  console.log('  有「出图」:', board.heads.includes('出图'), '｜有「出视频」:', board.heads.includes('出视频'));
  console.log('  已无「就绪态」:', !board.heads.includes('就绪态'), '｜已无「任务态」:', !board.heads.includes('任务态'));
  await p.screenshot({ path: OUT + '/clean_board.png' });
  console.log('  控制台:', errs.length ? errs : '无');

  errs = [];
  console.log('\n══════ 镜头详情 ══════');
  await p.goto(BASE + '/?_r=' + Date.now() + '#/p/1/shot/113', { waitUntil: 'load' });
  await p.waitForTimeout(2600);
  const det = await p.evaluate(() => {
    const cols = document.querySelector('.cols');
    const heads = [...document.querySelectorAll('.head button')].map((x) => x.innerText.trim());
    return {
      direction: cols ? getComputedStyle(cols).flexDirection : null,
      headButtons: heads,
      hasConfirm: heads.some((x) => /确认本镜|已确认/.test(x)),
      titleInput: !!document.querySelector('.head input'),
      titleText: (document.querySelector('.shot-title') || {}).innerText || null,
      wizLink: document.querySelectorAll('.wiz-link').length,
      wizLinkText: (document.querySelector('.wiz-link') || {}).innerText || null,
      hasSnippetWord: document.body.innerText.includes('片段库'),
      peTools: [...document.querySelectorAll('.pe-head')].map((h) =>
        [...h.querySelectorAll('button')].map((b) => b.innerText.trim()).join('/')),
    };
  });
  console.log('  .cols 方向:', det.direction, '（应为 column）');
  console.log('  顶栏按钮:', det.headButtons.join(' / ') || '（无）');
  console.log('  仍有「确认本镜」:', det.hasConfirm);
  console.log('  标题仍是可编辑输入框:', det.titleInput, '｜只读标题文本:', det.titleText);
  console.log('  正文里可点的镜头语言句:', det.wizLink, '处 →', JSON.stringify(det.wizLinkText));
  console.log('  页面还有「片段库」字样:', det.hasSnippetWord);
  console.log('  两个提示词工具栏:', det.peTools.join('  ||  '));
  await p.screenshot({ path: OUT + '/clean_detail.png' });
  console.log('  控制台:', errs.length ? errs : '无');

  console.log('\n══════ 镜头设置弹窗 ══════');
  errs = [];
  const btn = p.locator('.pe-head button', { hasText: '镜头设置' }).first();
  if (!(await btn.count())) {
    console.log('  !! 没找到「镜头设置」入口按钮');
  } else {
    await btn.click();
    await p.waitForTimeout(1000);
    const dlg = await p.evaluate(() => {
      const d = [...document.querySelectorAll('.el-dialog')].find((x) => x.getBoundingClientRect().width > 0);
      if (!d) return null;
      return {
        title: d.querySelector('.el-dialog__title')?.innerText,
        selects: d.querySelectorAll('.el-select').length,
        posCells: d.querySelectorAll('.pos-cell').length,
        figs: d.querySelectorAll('.wz-fig').length,
        actions: [...d.querySelectorAll('.actions button')].map((x) => x.innerText.trim()),
      };
    });
    console.log('  工具栏按钮点开:', JSON.stringify(dlg, null, 0));
    await p.screenshot({ path: OUT + '/clean_wizard.png' });

    await p.keyboard.press('Escape');
    await p.waitForTimeout(800);
    const link = p.locator('.wiz-link').first();
    if (await link.count()) {
      await link.click();
      await p.waitForTimeout(1000);
      const t2 = await p.evaluate(() => {
        const d = [...document.querySelectorAll('.el-dialog')].find((x) => x.getBoundingClientRect().width > 0);
        return d ? d.querySelector('.el-dialog__title')?.innerText : null;
      });
      console.log('  正文里点那句 → 弹窗:', t2);
    } else {
      console.log('  !! 正文里没找到可点句');
    }
  }
  console.log('  控制台:', errs.length ? errs : '无');

  await b.close();
})();
