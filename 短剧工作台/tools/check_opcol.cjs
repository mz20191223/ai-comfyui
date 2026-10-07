/* check_opcol.cjs — 表格「操作」列宽度体检（常驻工具，改完按钮/字号档后跑一次）
 *
 * 背景：全站操作列都用 .op-row（display:flex; flex-wrap:nowrap），
 * 列宽不够时右侧按钮会被 el-table 的 cell 直接裁掉（不报错、不换行）。
 * 而站点有 compact/normal/large/xlarge 四档字号，--fs-sm 从 12px 变到 16px，
 * 同一列宽在小屏/大字档下才暴露截断。
 *
 * 用法：node tools/check_opcol.cjs   （在项目根或任意路径都可，路径已写死）
 * 输出：每个操作列的估算所需宽度 vs 实际列宽，以及 !! 截断 标记。
 *
 * 估算规则（偏保守，宁可报宽不报窄）：
 *   中文/全角 = 1em；英文数字 = 0.58em；空格 = 0.3em
 *   按钮左右内边距 8px×2（见 styles.css .op-row .el-button）
 *   按钮相互间距 2px；单元格左右内边距 8px×2
 *   {{ 模板表达式 }} 按 1 个半角短串估（如 "(0)"）
 * v-if/v-else-if/v-else 分支内的按钮【互斥】，按分支取最大值，不累加。
 */
const fs = require('fs');
const path = require('path');

const ROOT = 'D:/Aicomfyui/短剧工作台/frontend/src';
const FS_SM = { compact: 12, normal: 13.5, large: 15, xlarge: 16 }; // :root 默认档 = large
const PAD_BTN = 16, GAP = 2, PAD_CELL = 16;

function textWidthEm(s) {
  let w = 0;
  for (const ch of s) {
    if (/[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef]/.test(ch)) w += 1;
    else if (/\s/.test(ch)) w += 0.3;
    else w += 0.58;
  }
  return w;
}

/* 把 op-row 里的按钮按「互斥分支」分组：遇到 v-if / v-else-if / v-else 就开新组 */
function groupsOf(block) {
  const inner = block.slice(block.indexOf('<div class="op-row">'));
  const parts = [];
  const re = /(<template\b[^>]*\bv-(?:if|else-if|else)\b[^>]*>)|(<el-button\b[^>]*?\bv-(?:if|else-if|else)\b[^>]*>)/g;
  let last = 0, m;
  const marks = [];
  while ((m = re.exec(inner))) marks.push(m.index);
  if (!marks.length) return [inner];
  parts.push(inner.slice(0, marks[0]));
  for (let i = 0; i < marks.length; i++) {
    parts.push(inner.slice(marks[i], i + 1 < marks.length ? marks[i + 1] : inner.length));
  }
  return parts;
}

function labelsIn(chunk) {
  const out = [];
  const re = /<el-button\b[^>]*>([\s\S]*?)<\/el-button>/g;
  let b;
  while ((b = re.exec(chunk))) {
    const t = b[1]
      .replace(/<[^>]*>/g, '')
      .replace(/\{\{[\s\S]*?\}\}/g, '(0)')
      .replace(/\s+/g, ' ')
      .trim();
    out.push(t);
  }
  return out;
}

const files = [];
(function walk(d) {
  for (const f of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, f.name);
    if (f.isDirectory()) walk(p);
    else if (f.name.endsWith('.vue')) files.push(p);
  }
})(ROOT);

const CO = /<el-table-column\b[^>]*class-name="op-col"[^>]*>[\s\S]*?<\/el-table-column>/g;

let bad = 0, total = 0;
console.log('判定 | 文件 | 列宽 | 同屏最多按钮 | compact/normal/large/xlarge 所需宽');
for (const p of files) {
  const s = fs.readFileSync(p, 'utf8');
  CO.lastIndex = 0;
  let m;
  while ((m = CO.exec(s))) {
    const block = m[0];
    const openTag = block.slice(0, block.indexOf('>') + 1);
    const wm = openTag.match(/(?<![-\w])width="(\d+)"/);
    const lm = openTag.match(/\blabel="([^"]*)"/);

    let best = { labels: [], need: null };
    for (const g of groupsOf(block)) {
      const lb = labelsIn(g);
      if (!lb.length) continue;
      const emSum = lb.reduce((a, t) => a + textWidthEm(t), 0);
      const need = {};
      for (const [k, fsz] of Object.entries(FS_SM)) {
        need[k] = Math.ceil(emSum * fsz + PAD_BTN * lb.length + GAP * (lb.length - 1) + PAD_CELL);
      }
      if (!best.need || Math.max(...Object.values(need)) > Math.max(...Object.values(best.need))) {
        best = { labels: lb, need };
      }
    }
    if (!best.need) continue;
    total++;
    const worst = Math.max(...Object.values(best.need));
    const ok = wm != null && worst <= Number(wm[1]);
    if (!ok) bad++;
    console.log(
      (ok ? ' OK  ' : ' !!  ') + p.replace(ROOT + '/', '').padEnd(26) +
      ' w=' + String(wm ? wm[1] : '?').padEnd(5) + ' n=' + best.labels.length + '  ' +
      `c:${best.need.compact} n:${best.need.normal} l:${best.need.large} x:${best.need.xlarge}` +
      (ok ? '' : `   ← 超出 ${worst - Number(wm[1])}px`)
    );
    if (!ok) console.log('       按钮: ' + best.labels.join(' / ') + (lm ? `   [${lm[1]}]` : ''));
  }
}
console.log(bad ? `CLIP_FOUND=${bad} / TOTAL=${total}` : `ALL_FIT / TOTAL=${total}`);
