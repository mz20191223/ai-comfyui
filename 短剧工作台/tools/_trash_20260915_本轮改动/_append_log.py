#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把本轮改动追加到今日日志（append-only）。"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Administrator\WorkBuddy\2026-08-27-16-21-46\.workbuddy\memory\2026-09-16.md"

ADD = """

## 操作列统一居中（用户反馈「操作表头没居中，看着别扭」）
- 根因：Element Plus 表头默认 text-align:left，`.op-row` 是 flex 左对齐 → 操作列较宽时（项目列表 380px）表头文字与按钮组一起靠左，右侧留空显得悬空。
- 做法：全站 **17 个「操作」列**统一加 `class-name="op-col" label-class-name="op-col"`（Creation×2 / Health / Projects / PromptCenter×4 / Script×2 / Settings×4 / ShotBoard / TaskCenter / Timeline）；
  样式加在 `styles.css`：`.el-table .op-col .cell{text-align:center}` + `.el-table .op-col .cell .op-row{justify-content: safe center}`。
- **用 `safe center` 而非 `center`**：万一某档字号下按钮超宽，会自动退回左对齐而不是两边裁切；不认识该值的浏览器直接忽略该声明，退回原有左对齐行为。
- 新增探针 `tools/probe_alignment.cjs`（量「表头中线 vs 按钮中线」，项目列表实测 1378 == 1378 ✓）、`tools/probe_page.cjs`（单页诊断：控制台报错 / 失败请求 / body 内文）。
- `probe_oprow.cjs` 复跑：**84 处操作列全部单行、无溢出，异常 0**；`vite build` exit=0。

## 顺带修掉一个脚本陈旧项（不是本次改动引起的）
- `smoke_pages.cjs` / `probe_oprow.cjs` 里还在测 `/#/p/1/overview`，但 **`Overview.vue` 与对应路由都已不存在**（router/index.js 里没有 overview）→ 该 URL 渲染 `<!---->`，冒烟一直报 1 页异常。
- 已把该项换成新页 `/p/1/script`，冒烟复跑 **11/11 通过、异常 0**。

## 项目记忆整理
- `MEMORY.md` 曾 34.3KB 被注入截断。已重写为**高频铁律 + 索引**（9.1K 字符），完整细节（通道请求体、镜头14逐镜表、H3 提示词官方写法、示意图做法、逐条踩坑）留档到同目录 **`MEMORY-详细档案.md`**。
"""

with io.open(P, "a", encoding="utf-8") as f:
    f.write(ADD)
print("已追加，日志现在", len(open(P, encoding="utf-8").read()), "字符")
print("文件存在:", os.path.exists(P))
