# -*- coding: utf-8 -*-
"""收尾：追加今日日志（题材下拉）。"""
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"D:\Aicomfyui\短剧工作台"
LOG = r"C:\Users\Administrator\WorkBuddy\2026-08-27-16-21-46\.workbuddy\memory\2026-09-16.md"

ADD = """

## 「题材」由自由输入框改为可选下拉（用户连问两次「为啥不能选择」）
- **用户的困惑来源**：`Projects.vue` 新建/编辑项目里那格「题材 / 风格」原本是 `el-input`，**placeholder 恰好是灰字「软科幻·神话」**，
  而紧挨右边那格「画面风格」是 `el-select`（有下拉箭头）。灰字看起来太像真实选项值 + 左边没箭头 → 被当成"选不了的下拉"。
  （剧本页那格里的「软科幻·神话」是**真值**，由 `load()` 从 `p.genre` 自动带入：`if (!form.value.genre) form.value.genre = p.genre || ''`。）
- **改法**（两处统一，不再有"看起来像选项的灰字"）：
  - 新增 `frontend/src/constants.js`：`GENRES`（28 个常见短剧题材）+ `genreOptions(current)`（**当前值不在预设里时排到最前**，保证历史自定义题材也能正常显示为选中项）。
  - `Script.vue` 参数行「题材」：`el-input` → `el-select filterable allow-create default-first-option clearable`，宽 110→**152px**（要放得下「软科幻·神话」6 字 + 箭头）。
  - `Projects.vue` 新建/编辑项目「题材 / 风格」：同样换成 select（宽 200px 不变），placeholder 由误导性的「软科幻·神话」改为「选一个题材，或直接输入新的」。
- **设计取舍**：用 `filterable + allow-create` 而不是纯固定下拉 —— 既能"选"，也不堵死以后的新题材；题材这类词表枚举不全反而更碍事。
- **验证**（`tools/probe_genre.cjs`，真实浏览器）：剧本页题材已是 select、29 项（当前值排首）、能选中「悬疑推理」、能自输新词「赛博朋克外卖」回车生效；
  新建项目页同为 select、28 项；控制台 0 报错、0 失败请求；`smoke_pages.cjs` **11/11 通过**；库中项目 1 题材仍为「软科幻·神话」（巡检未写入任何数据）。
"""
with io.open(LOG, "a", encoding="utf-8") as f:
    f.write(ADD)
print("日志已追加，现", len(open(LOG, encoding="utf-8").read()), "chars")
