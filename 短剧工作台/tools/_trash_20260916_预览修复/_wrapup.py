# -*- coding: utf-8 -*-
"""收尾：归档本轮临时自检脚本 + 追加今日工作日志。"""
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"D:\Aicomfyui\短剧工作台"
TRASH = os.path.join(ROOT, "tools", "_trash_20260916_预览修复")
os.makedirs(TRASH, exist_ok=True)

for n in ("_chk_preview.py", "_chk_preview_api.py", "_chk_preview_full.py", "_chk_cfg.py"):
    s = os.path.join(ROOT, "tools", n)
    if os.path.exists(s):
        shutil.move(s, os.path.join(TRASH, n))
        print("已归档", n)

print("tools 里 _ 开头:", [n for n in sorted(os.listdir(os.path.join(ROOT, "tools"))) if n.startswith("_")])

LOG = r"C:\Users\Administrator\WorkBuddy\2026-08-27-16-21-46\.workbuddy\memory\2026-09-16.md"
ADD = """

## 修「预览提示词」点了没反应（用户报障）
- **根因**：后端 `POST /projects/{pid}/scripts/preview` 走 `_script_or_latest()` 取正文，**没有剧本就 raise 400「还没有剧本内容，请先生成或录入剧本」** → 前端 `withBusy` catch 后弹红条。
  可预览本来就是「生成前先看要发什么」，这个前置校验完全多余。
- **顺带发现第二个真 bug**：前端「按意见重写」发的是 `instruction`（Script.vue doRevise），但后端 `ReviseIn` **没有 instruction 字段** → 被 pydantic 忽略，
  真正的「修改意见」变成了顶部「创作要求」框的内容（为空时退化成默认句「整体打磨，增强节奏与钩子」）。→ `ReviseIn` 加 `instruction`，`revise` 用 `instruction or requirement`。
- **改法**：`/preview` 改为**永不 400**，一次返回两套草稿：
  `{"generate": {...}, "revise": {...}|null, "content_note": "第N版"}`（有剧本时才有 revise）。前端弹窗加 `el-radio-button` 双档「生成会发的内容 / 按意见重写」（无剧本时后者 disabled），`previewText` 由 ref 改为 computed。
- **验证**：无剧本时 HTTP 200 / generate 337 字（含【题材】【画面风格】【画幅】【体量】【创作要求】）；临时项目（建→存一版→预览→删）验证 revise 同时带上「修改意见原文 + 现有剧本原文」、且 `instruction` 优先于 `requirement`；
  真实浏览器点击巡检 `tools/probe_preview.cjs`：弹窗出现、326 字 2 条消息、控制台 0 报错、0 失败请求。临时项目已删，**无孤儿数据**（项目删除会级联清 scripts）。
- 新增探针：`tools/probe_preview.cjs`（点按钮抓弹窗内容）、`tools/probe_reqrow.cjs`（读参数行各控件实际 value/placeholder）。

## 澄清「题材」为什么不能选（用户问）
- 剧本页参数行那格「**题材」是自由输入框 `el-input`**（不是下拉），所以点不出候选；右边那格「画面风格」才是 `el-select`（写实真人/动漫/3D）。
- 里面显示的「软科幻·神话」**不是浏览器自动补全，是程序自动带出来的**——`Script.vue` `load()` 里：
  `if (!form.value.genre) form.value.genre = p.genre || ''`、`visual_style` 同款（默认 `live_action`）。即**打开页面时把项目的题材/风格填进来**。
- 另：项目编辑页「题材 / 风格」也是自由输入框，其 placeholder 恰好就是「软科幻·神话」（易与真实值混淆）。

## ⚠️ 更正上一轮的错误结论：DeepSeek 密钥**早就在密钥池里**
- 上一轮我查密钥池时报「密钥池是空的」，实为**自己那条 SQL 执行失败**（`LEFT(api_key,10)` 那句抛错后脚本中断），把「查询失败」误读成「没数据」。
- 实际 `provider_credentials`：id6 = provider 3(deepseek) / alias「主号」/ `sk-abaa21c34…` / enabled=1 / status=active。→ 剧本生成**不需要再配 key**。
- 教训：**查询报错 ≠ 数据为空**，SQL 必须逐句 try/except 并打印异常。

## 踩坑
- `Edit` 工具在此类文件上可用（本轮 `scripts.py` / `Script.vue` 均为 LF）；上一轮 `task_runner.py` 是 CRLF 才匹配不上，需走补丁脚本。
- 一次性 python -c 里混用多层引号 + 中文路径容易炸（本轮 exit=1 且无输出），**改用 `Write` 落临时脚本再执行**更稳。
"""
with io.open(LOG, "a", encoding="utf-8") as f:
    f.write(ADD)
print("日志已追加，现", len(open(LOG, encoding="utf-8").read()), "chars")
