/**
 * CloudBase 生图工坊 —— 本地代理服务（零依赖，仅用 Node 内置模块）
 *
 * 职责：
 *   1. 托管前端页面 index.html
 *   2. /api/expand  → 调用 CloudBase 生文接口，把短句扩写成英文图像提示词
 *   3. /api/image  → 调用 CloudBase 生图接口，返回图片 URL
 *
 * 安全：API Key 只存在本机 config.json / 环境变量里，且服务只监听 127.0.0.1，
 *       不会暴露给浏览器或外网。请勿把 API Key 写进前端页面。
 *
 * 运行：node server.js   （Node 18+，无需 npm install）
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

// ---------- 读取配置 ----------
const CONFIG_PATH = path.join(__dirname, 'config.json');
let config = {};
try {
  config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
} catch (e) {
  console.error('[错误] 读取 config.json 失败：', e.message);
  process.exit(1);
}

const ENV_ID = process.env.CB_ENV_ID || config.ENV_ID;
const API_KEY = process.env.CB_API_KEY || config.API_KEY;
if (!ENV_ID || !API_KEY || ENV_ID === 'YOUR_ENV_ID' || API_KEY === 'YOUR_API_KEY') {
  console.error('[错误] 请在 config.json 填写 ENV_ID 和 API_KEY，或用环境变量 CB_ENV_ID / CB_API_KEY 传入。');
  process.exit(1);
}

const PORT = process.env.PORT || config.PORT || 3000;
const TEXT_MODEL = config.TEXT_MODEL || 'hunyuan-turbos-latest';
const IMAGE_MODEL = config.IMAGE_MODEL || 'HY-Image-3.0-Plus-4090-Tob-v1.0';
const ALLOWED_SIZES = ['1024x1024', '1280x720', '720x1280', '1280x1280'];

// 用真实 ENV_ID 替换占位符
function subEnv(u) { return (u || '').replace(/\$\{ENV_ID\}/g, ENV_ID); }

// 生文接口（官方确认）：/v1/ai/cloudbase/chat/completions
const TEXT_URL = subEnv(
  config.TEXT_URL || 'https://${ENV_ID}.api.tcloudbasegateway.com/v1/ai/cloudbase/chat/completions'
);
// 生图接口有两种候选路径，依次尝试（详见 README）：provider 写法 与 env 写法
const IMAGE_URL_CANDIDATES = [
  subEnv(config.IMAGE_URL) || null, // 若用户在 config 显式指定，优先用
  `https://${ENV_ID}.api.tcloudbasegateway.com/v1/ai/hunyuan-image/images/ar/generations`,
  `https://${ENV_ID}.api.tcloudbasegateway.com/v1/ai/${ENV_ID}/images/ar/generations`,
].filter(Boolean);

// ---------- 调用 CloudBase 生文（扩写提示词） ----------
async function expandPrompt(prompt) {
  const sys = [
    'You are a professional AI image-prompt engineer.',
    'The user gives you a short Chinese description. Rewrite it into a detailed, vivid English image-generation prompt.',
    'Include: subject description, art style (e.g. Pixar 3D animated style), composition, lighting, color mood, and material detail.',
    'Output ONLY the expanded English prompt itself. No explanation, no quotes, no prefixes.'
  ].join(' ');

  const body = {
    model: TEXT_MODEL,
    messages: [
      { role: 'system', content: sys },
      { role: 'user', content: prompt }
    ],
    stream: false,
    temperature: 0.85
  };

  const resp = await fetch(TEXT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API_KEY },
    body: JSON.stringify(body)
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const msg = (data && data.error && data.error.message) || JSON.stringify(data);
    throw new Error('生文接口错误(' + resp.status + ')：' + msg);
  }
  const content = data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
  if (!content) throw new Error('生文接口返回格式异常：' + JSON.stringify(data));
  return content.trim();
}

// ---------- 调用 CloudBase 生图 ----------
async function generateImage(prompt, size) {
  if (!ALLOWED_SIZES.includes(size)) size = '1024x1024';
  const body = {
    model: IMAGE_MODEL,
    prompt: prompt,
    size: size,
    revise: { value: true } // 让模型自动优化提示词
  };

  let lastErr = null;
  for (const url of IMAGE_URL_CANDIDATES) {
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API_KEY },
        body: JSON.stringify(body)
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const msg = (data && data.error && data.error.message) || JSON.stringify(data);
        lastErr = new Error('生图接口错误(' + resp.status + ')@' + url + '：' + msg);
        // 404 说明路径不对，尝试下一个候选；其它错误直接抛出
        if (resp.status === 404) { console.warn('[warn] 生图路径 404，尝试下一个候选：', url); continue; }
        throw lastErr;
      }
      const item = (data.data && data.data[0]) || {};
      const imgUrl = item.url;
      if (!imgUrl) throw new Error('生图接口返回格式异常：' + JSON.stringify(data));
      return { url: imgUrl, revised: item.revised_prompt || data.revised_prompt || '', triedUrl: url };
    } catch (e) {
      if (e.message && e.message.indexOf('404') === -1) throw e;
      lastErr = e;
    }
  }
  throw lastErr || new Error('生图接口所有候选路径均失败');
}

// ---------- 工具：读取请求 JSON body ----------
function readJson(req) {
  return new Promise((resolve, reject) => {
    let buf = '';
    req.on('data', c => { buf += c; if (buf.length > 1e6) req.destroy(); });
    req.on('end', () => {
      try { resolve(buf ? JSON.parse(buf) : {}); } catch (e) { reject(e); }
    });
    req.on('error', reject);
  });
}

// ---------- HTTP 服务 ----------
const server = http.createServer(async (req, res) => {
  const url = req.url.split('?')[0];

  // 前端页面
  if (req.method === 'GET' && (url === '/' || url === '/index.html')) {
    fs.readFile(path.join(__dirname, 'index.html'), (err, html) => {
      if (err) { res.writeHead(500); res.end('index.html not found'); return; }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
    });
    return;
  }

  // 扩写
  if (req.method === 'POST' && url === '/api/expand') {
    try {
      const { prompt } = await readJson(req);
      if (!prompt || !prompt.trim()) { res.writeHead(400); res.end(JSON.stringify({ error: '请输入描述' })); return; }
      const expanded = await expandPrompt(prompt.trim());
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ expanded }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // 生图
  if (req.method === 'POST' && url === '/api/image') {
    try {
      const { prompt, size } = await readJson(req);
      if (!prompt || !prompt.trim()) { res.writeHead(400); res.end(JSON.stringify({ error: '请输入或先扩写提示词' })); return; }
      const result = await generateImage(prompt.trim(), size);
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(result));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  res.writeHead(404); res.end('Not Found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('========================================');
  console.log(' CloudBase 生图工坊 已启动');
  console.log(' 打开浏览器访问： http://localhost:' + PORT);
  console.log(' 环境 ENV_ID : ' + ENV_ID);
  console.log(' 生文模型    : ' + TEXT_MODEL);
  console.log(' 生图模型    : ' + IMAGE_MODEL);
  console.log(' 仅监听 127.0.0.1，API Key 不外泄');
  console.log('========================================');
});
