/**
 * 浏览器验证：镜头详情页的「音频素材」区
 * - 已有音频的镜头（113 / 镜头14c）：显示文件名、实测时长、播放器、更换/摘掉按钮
 * - 音频文件缺失的镜头（115 / 镜头17）：只显示文件名，无播放器
 * - 「选择音频文件」弹窗：默认筛选音频类型、能列出 mp3
 *
 * 用法：node tools/probe_shot_audio.cjs
 */
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core';
const { chromium } = require(PW);
const BASE = 'http://127.0.0.1:5192';
const EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = 'D:/Aicomfyui/短剧工作台/storage/ui-tour';

const readCard = () => {
  const cards = [...document.querySelectorAll('.card')];
  const card = cards.find((c) => /音频|台词窗口|本镜无台词/.test(c.innerText || ''));
  if (!card) return null;
  return {
    text: (card.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 400),
    buttons: [...card.querySelectorAll('.el-button')].map((b) => (b.innerText || '').trim()).filter(Boolean),
    hasPlayer: !!card.querySelector('audio'),
  };
};

(async () => {
  const b = await chromium.launch({ headless: true, executablePath: EXE });
  const ctx = await b.newContext({ viewport: { width: 1600, height: 1000 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 200)));

  for (const [sid, label] of [['113', '镜头14c（音频存在）'], ['115', '镜头17（音频文件缺失）']]) {
    await p.goto(`${BASE}/#/p/1/shot/${sid}`, { waitUntil: 'load', timeout: 30000 });
    await p.waitForFunction(() => document.body.innerText.includes('音频与校验'), { timeout: 25000 }).catch(() => {});
    await p.waitForTimeout(1200);
    const card = await p.evaluate(readCard);
    console.log(`\n【${label}】#/p/1/shot/${sid}`);
    if (!card) { console.log('  !! 未找到音频卡片'); continue; }
    console.log('  文字:', card.text.slice(0, 180));
    console.log('  按钮:', card.buttons.join(' / '));
    console.log('  播放器:', card.hasPlayer ? '有' : '无');
    await p.screenshot({ path: `${OUT}/shot_audio_${sid}.png` });
  }

  // 打开「选择音频文件」弹窗
  await p.goto(`${BASE}/#/p/1/shot/115`, { waitUntil: 'load', timeout: 30000 });
  await p.waitForFunction(() => document.body.innerText.includes('音频与校验'), { timeout: 25000 }).catch(() => {});
  await p.waitForTimeout(1200);
  const clicked = await p.evaluate(() => {
    const btn = [...document.querySelectorAll('.el-button')].find((x) => /选择音频文件|更换音频/.test(x.innerText || ''));
    if (!btn) return false;
    btn.click();
    return true;
  });
  console.log('\n【选择音频文件弹窗】按钮点击:', clicked);
  await p.waitForTimeout(1500);
  const dlg = await p.evaluate(() => {
    const d = [...document.querySelectorAll('.el-dialog')].filter((x) => x.offsetParent !== null).pop();
    if (!d) return null;
    return {
      title: (d.querySelector('.el-dialog__title')?.innerText || '').trim(),
      kind: [...d.querySelectorAll('.el-radio-button')].filter((x) => /is-active/.test(x.className)).map((x) => x.innerText.trim()),
      names: [...d.querySelectorAll('.thumb .cap')].map((x) => x.innerText.trim()).slice(0, 8),
      count: d.querySelectorAll('.thumb').length,
      footer: [...d.querySelectorAll('.el-button')].map((x) => (x.innerText || '').trim()).filter(Boolean),
    };
  });
  if (dlg) {
    console.log('  弹窗标题:', dlg.title);
    console.log('  当前筛选:', dlg.kind.join(',') || '(未选中)');
    console.log('  列出文件数:', dlg.count);
    dlg.names.forEach((n) => console.log('    -', n.slice(0, 70)));
    console.log('  底部按钮:', dlg.footer.join(' / '));
    await p.screenshot({ path: `${OUT}/shot_audio_picker.png` });
  } else {
    console.log('  !! 弹窗未打开');
  }

  // 真实点击一遍：在 113 上重挂「同一个文件」——验证 UI→接口 全链路，且不改动任何数据
  await p.goto(`${BASE}/#/p/1/shot/113`, { waitUntil: 'load', timeout: 30000 });
  await p.waitForFunction(() => document.body.innerText.includes('音频与校验'), { timeout: 25000 }).catch(() => {});
  await p.waitForTimeout(1000);
  await p.evaluate(() => {
    const btn = [...document.querySelectorAll('.el-button')].find((x) => /更换音频/.test(x.innerText || ''));
    btn && btn.click();
  });
  await p.waitForTimeout(1500);
  const picked = await p.evaluate(() => {
    const d = [...document.querySelectorAll('.el-dialog')].filter((x) => x.offsetParent !== null).pop();
    if (!d) return null;
    const t = [...d.querySelectorAll('.thumb')].find((x) => /镜头14c/.test(x.innerText || ''));
    if (!t) return 'FILE-NOT-FOUND';
    t.click();
    const ok = [...d.querySelectorAll('.el-button')].find((x) => /使用选中文件/.test(x.innerText || ''));
    ok && ok.click();
    return 'CLICKED';
  });
  console.log('\n【真实挂载·镜头14c 重挂同一文件】选择结果:', picked);
  await p.waitForTimeout(2500);
  const after = await p.evaluate(readCard);
  console.log('  挂载后文字:', (after?.text || '').slice(0, 120));
  console.log('  播放器:', after?.hasPlayer ? '有' : '无');

  console.log('\n控制台错误:', errs.length ? errs.slice(0, 4).join(' | ') : '无');
  await b.close();
})();
