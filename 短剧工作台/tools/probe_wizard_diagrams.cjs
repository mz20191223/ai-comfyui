/**
 * 浏览器验证：镜头设置向导的「三张示意图 + 注入句预览」
 *
 * 只读，不点「写入并注入提示词」（不写库）。
 * 检查：
 * 1. 景别下拉：每个选项都是一张生成图，且真实加载成功
 * 2. 视角下拉：同上
 * 3. 运镜下拉：每个选项是代码画的俯视机位图（SVG 有内容，不是空框）
 * 4. 预览区：选满后并排出现 景别图 / 视角图 / 运镜图
 * 5. 注入句两行说明由后端给出（分镜图句 / 视频句）
 *
 * 用法：node tools/probe_wizard_diagrams.cjs
 */
const PW = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/@playwright/cli/node_modules/playwright-core'
const { chromium } = require(PW)
const BASE = 'http://127.0.0.1:5192'
const EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const OUT = 'D:/Aicomfyui/短剧工作台/storage/ui-tour'

const dropdownInfo = () =>
  [...document.querySelectorAll('.el-select-dropdown')]
    .filter((d) => d.offsetParent !== null)
    .map((d) => {
      const imgs = [...d.querySelectorAll('.opt-img')]
      const svgs = [...d.querySelectorAll('.opt-row svg')]
      return {
        rows: d.querySelectorAll('.el-select-dropdown__item').length,
        imgs: imgs.length,
        imgsLoaded: imgs.filter((i) => i.naturalWidth > 0).length,
        imgSample: imgs[0] ? `${imgs[0].naturalWidth}x${imgs[0].naturalHeight} ${imgs[0].src.split('/').pop()}` : null,
        svgs: svgs.length,
        svgInk: svgs.filter((s) => s.querySelectorAll('path,line,circle,rect').length > 3).length,
      }
    })

const previewInfo = () => {
  const figs = [...document.querySelectorAll('.wz-fig')]
  return {
    figs: figs.length,
    detail: figs.map((f) => {
      const img = f.querySelector('img')
      const svg = f.querySelector('svg')
      return {
        cap: (f.querySelector('figcaption')?.innerText || '').trim(),
        kind: img ? 'img' : svg ? 'svg' : '?',
        size: img
          ? `${img.naturalWidth}x${img.naturalHeight}(${img.src.split('/').pop()})`
          : svg
            ? `${Math.round(svg.getBoundingClientRect().width)}x${Math.round(svg.getBoundingClientRect().height)} ink=${svg.querySelectorAll('path,line,circle,rect').length}`
            : '-',
      }
    }),
    lines: [...document.querySelectorAll('.wz-line')].map((l) =>
      (l.innerText || '').replace(/\s+/g, ' ').trim(),
    ),
  }
}

;(async () => {
  const b = await chromium.launch({ headless: true, executablePath: EXE })
  const ctx = await b.newContext({ viewport: { width: 1680, height: 1100 } })
  const p = await ctx.newPage()
  const errs = []
  const bad = []
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)) })
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 200)))
  p.on('response', (r) => {
    const u = r.url()
    if (u.includes('/shot-diagrams/') && r.status() >= 400) bad.push(`${r.status()} ${u.split('/').pop()}`)
    if (r.status() >= 500) bad.push(`${r.status()} ${u.replace(BASE, '')}`)
  })

  await p.goto(`${BASE}/#/p/1/shot/90`, { waitUntil: 'load', timeout: 30000 })
  await p.waitForFunction(() => document.body.innerText.includes('首帧锚点'), { timeout: 25000 }).catch(() => {})
  await p.waitForTimeout(1200)

  await p.click('.wz-head')
  await p.waitForTimeout(600)

  const selects = await p.$$('.wizard .el-select')
  console.log('向导内下拉数:', selects.length, '（景别 / 视角 / 运镜 / 远近）')

  for (const [i, name] of [[0, '景别'], [1, '视角'], [2, '运镜']]) {
    await selects[i].click()
    await p.waitForTimeout(700)
    const info = await p.evaluate(dropdownInfo)
    console.log(`\n【${name}下拉】`, JSON.stringify(info))
    await p.screenshot({ path: `${OUT}/wz_dd_${i}_${name}.png` })
    // 选第一项，让预览区出现对应示意图
    await p.keyboard.press('ArrowDown')
    await p.keyboard.press('Enter')
    await p.waitForTimeout(600)
  }

  console.log('\n【预览区】', JSON.stringify(await p.evaluate(previewInfo), null, 1))

  const wz = await p.$('.wizard')
  await wz.screenshot({ path: `${OUT}/wz_panel.png` })

  // 再走一遍运镜全部 11 项，确认每项都画得出来
  await selects[2].click()
  await p.waitForTimeout(500)
  const mv = await p.evaluate(() => {
    const items = [...document.querySelectorAll('.el-select-dropdown__item')]
    return items.map((it) => {
      const s = it.querySelector('svg')
      return {
        label: (it.innerText || '').trim(),
        ink: s ? s.querySelectorAll('path,line,circle,rect').length : 0,
      }
    })
  })
  console.log('\n【运镜 11 项示意图形状数】')
  mv.forEach((m) => console.log(`   ${m.label.padEnd(6)} ${m.ink}`))
  await p.screenshot({ path: `${OUT}/wz_dd_movement_all.png` })
  await p.keyboard.press('Escape')
  await p.waitForTimeout(300)

  console.log('\n════ 控制台');
  console.log(errs.length ? errs.map((e) => '  ✕ ' + e).join('\n') : '  ✓ 零异常')
  console.log('图缺失/5xx:', bad.length ? bad.join(', ') : '无')

  await b.close()
})()
