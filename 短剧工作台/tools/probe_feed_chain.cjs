/**
 * 浏览器验证：镜头详情页的「素材投喂链路 + 镜头设置向导」
 *
 * 检查四件事：
 * 1. 首帧锚点条：显示当前 ref_image_0、来源标注、上一镜尾帧下拉是否有候选
 * 2. 参考图区：只列能解析到真文件的；幽灵引用收进折叠警告
 * 3. take_note 长描述默认隐藏，点「看用途」才展开
 * 4. 镜头设置向导：展开后能选，实时预览分两路（分镜图静态 / 视频动态）
 *
 * 用法：node tools/probe_feed_chain.cjs
 */
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW);
const BASE = 'http://127.0.0.1:5192';
const EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = 'D:/Aicomfyui/短剧工作台/storage/ui-tour';

const readAnchor = () => {
  const el = document.querySelector('.anchor');
  if (!el) return null;
  return {
    text: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 300),
    hasSelect: !!el.querySelector('.el-select'),
  };
};

const readRefs = (paneIndex) => {
  const panes = [...document.querySelectorAll('.pane')];
  const pane = panes[paneIndex];
  if (!pane) return null;
  const head = pane.querySelector('.ref-head');
  const bad = pane.querySelector('.bad-box');
  const tiles = [...pane.querySelectorAll('.tile')];
  return {
    head: head ? (head.innerText || '').replace(/\s+/g, ' ').trim() : null,
    validRows: tiles.length,
    withImg: tiles.filter((t) => { const i = t.querySelector('img'); return i && i.naturalWidth > 0 }).length,
    badText: bad ? (bad.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120) : null,
    noteHidden: !pane.querySelector('.note'),
    opsOnHover: !!pane.querySelector('.tile-ops'),
  };
};

const readWizard = () => {
  const el = document.querySelector('.wizard');
  if (!el) return null;
  const lines = [...el.querySelectorAll('.wz-line')].map((l) => (l.innerText || '').replace(/\s+/g, ' ').trim());
  return {
    head: (el.querySelector('.wz-head')?.innerText || '').replace(/\s+/g, ' ').trim(),
    selects: [...el.querySelectorAll('.el-select')].length,
    posCells: [...el.querySelectorAll('.pos-cell')].length,
    lines,
  };
};

(async () => {
  const b = await chromium.launch({ headless: true, executablePath: EXE });
  const ctx = await b.newContext({ viewport: { width: 1680, height: 1050 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 200)));

  for (const [sid, label] of [['91', '镜头4'], ['92', '镜头5'], ['111', '镜头14b-1'], ['115', '镜头17']]) {
    await p.goto(`${BASE}/#/p/1/shot/${sid}`, { waitUntil: 'load', timeout: 30000 });
    await p.waitForFunction(() => document.body.innerText.includes('首帧锚点'), { timeout: 25000 }).catch(() => {});
    await p.waitForTimeout(1500);

    console.log(`\n════ ${label}（#/p/1/shot/${sid}）`);

    const anchor = await p.evaluate(readAnchor);
    console.log('【首帧锚点条】');
    console.log('  ', anchor ? anchor.text : '!! 没渲染');

    for (const [idx, side] of [[0, '分镜图'], [1, '视频']]) {
      const r = await p.evaluate(readRefs, idx);
      console.log(`【${side}参考图区】`);
      if (!r) { console.log('   !! 没渲染'); continue; }
      console.log('   统计行:', r.head, '｜卡片:', r.validRows, '张（缩略图已加载', r.withImg, '张）');
      console.log('   幽灵折叠:', r.badText || '（无）');
      console.log('   用途长句默认隐藏:', r.noteHidden ? '是' : '否', '｜悬停操作层:', r.opsOnHover ? '有' : '无');
    }

    const wz0 = await p.evaluate(readWizard);
    console.log('【镜头设置】折叠态:', wz0 ? wz0.head : '!! 没渲染');

    await p.click('.wz-head');
    await p.waitForTimeout(500);
    const wz = await p.evaluate(readWizard);
    const dia = await p.evaluate(() => {
      const figs = [...document.querySelectorAll('.wz-fig')];
      return {
        figs: figs.length,
        detail: figs.map((f) => {
          const img = f.querySelector('img');
          const svg = f.querySelector('svg');
          return img
            ? `${img.src.split('/').pop()} ${img.naturalWidth}x${img.naturalHeight}`
            : svg ? `svg(ink=${svg.querySelectorAll('path,line,circle,rect').length})` : '?';
        }),
      };
    });
    console.log('【镜头设置】展开: 下拉', wz.selects, '｜九宫格', wz.posCells, '｜预览', JSON.stringify(wz.lines));
    console.log('【示意图】预览区三图:', dia.figs, '张 →', dia.detail.join('  '));

    // 打开景别下拉，验证每个选项都带示意图
    await p.click('.wizard .el-select');
    await p.waitForTimeout(600);
    const optFigs = await p.evaluate(() => {
      const dd = [...document.querySelectorAll('.el-select-dropdown')].filter((d) => d.offsetParent !== null)[0];
      if (!dd) return { imgs: 0, loaded: 0, svgs: 0 };
      const imgs = [...dd.querySelectorAll('.opt-img')];
      return {
        imgs: imgs.length,
        loaded: imgs.filter((i) => i.naturalWidth > 0).length,
        svgs: dd.querySelectorAll('.opt-row svg').length,
      };
    });
    console.log('【示意图】景别下拉: 生成图', optFigs.imgs, '张（已加载', optFigs.loaded, '）｜应为 7 张全加载');
    await p.keyboard.press('Escape');
    await p.waitForTimeout(300);

    const cells = await p.$$('.pos-cell');
    if (cells[8]) {
      await cells[8].click();
      await p.waitForTimeout(300);
      console.log('   点「右下」后:', JSON.stringify((await p.evaluate(readWizard)).lines));
      await cells[8].click();
      await p.waitForTimeout(200);
    }

    await p.screenshot({ path: `${OUT}/feed_chain_${sid}.png`, fullPage: true });
  }

  console.log('\n════ 控制台');
  console.log(errs.length ? errs.map((e) => '  ✕ ' + e).join('\n') : '  ✓ 零异常');

  await b.close();
})();
