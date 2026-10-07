# -*- coding: utf-8 -*-
"""归档本轮临时脚本 + 追加今日日志。"""
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\Aicomfyui\短剧工作台"
TRASH = os.path.join(ROOT, "tools", "_trash_20260916_删除预审与整集Lint")
os.makedirs(TRASH, exist_ok=True)

for n in ("_rm_plan_lint.py", "_rm_plan_only.py", "_chk_rm_plan.py"):
    s = os.path.join(ROOT, "tools", n)
    if os.path.exists(s):
        shutil.move(s, os.path.join(TRASH, n))
        print("已归档", n)

LOG = r"C:\Users\Administrator\WorkBuddy\2026-08-27-16-21-46\.workbuddy\memory\2026-09-16.md"
add = """

## 删除「生成方案预审」与「整集 Lint」（用户明确不需要）
- 用户原话：「生成方案预审——这个没啥必要，我都是一集集点击生成的」「整集 Lint 又是啥，我也不需要」。这两个是当初照别家工作流抄来的**批量**功能，与用户逐镜/逐集点生成的实际习惯不符。
- 删除范围（前后端全删，不留半死不活的代码）：
  - `ShotBoard.vue`：2 个按钮 + 2 个弹窗（36 行模板）+ 6 个 ref + `showPlan()` / `lintAll()`；9454 → 后 193 行
  - `Creation.vue`：操作列「生产方案」按钮 + 弹窗 + `planDlg`/`planData` + `openPlan()`
  - `api/index.js`：`productionPlan` / `lintEpisode`
  - `backend/app/routers/shots.py`：`POST /episodes/{id}/lint` 路由
  - `backend/app/routers/creation.py`：`POST /creation/episodes/{id}/production-plan` 整段（文件末函数，518 → 462 行），顺手清掉失效的 `naming` import
- **保留**：单镜 Lint（`POST /shots/{id}/lint` + `LintPanel.vue`）、Lint 规则管理（PromptCenter「Lint 规则」tab + `/lint-rules` `/lint-checkers`）。删的是「整集批量」入口，不是 Lint 能力本身。
- 验证：老接口 405、保留接口全 200；冒烟 11/11 异常 0；`vite build` exit=0。删除脚本全程带内容断言（写偏一行就报错不动文件），实际靠断言拦下 3 次定位偏差。
- 顺手修 `tools/ui_tour.cjs` 里同类陈旧项：「项目总览 `#/p/1/overview`」页面与路由早已不存在 → 换成 `#/p/1/script`，导航检查项同步去掉「总览看板」。
- ⚠️ 已知死代码（本次未动）：`backend/app/routers/projects.py` 的 `GET /projects/{id}/overview` 已无前端页面调用。

## 用户对创作主链路的新要求（方向性，待实施）
用户澄清后的完整链路：**新建项目 → 写剧本（DeepSeek 一次出稿，且出稿时就已分好集）→ 每集内容落到对应分集版块 → 每集必须包含【分镜图提示词（含分镜文字描述）】与【分镜视频提示词】→ 角色三视图/场景道具图走「先调 DeepSeek 出图片提示词，再调 gpt 出图」→ 一集确定无误后再出提示词并回填到每个镜头**。
- 关键差异：现有工作台是「剧本整篇 → 单独一步 AI 分集 → 正则拆镜 → 套模板生成提示词」；用户要的是**生成剧本时就带上集结构 + 每集镜头 + 双份提示词**，一步到位后落库/回填。
- 待定决策点：① 一次出全剧 vs 按集分批出提示词（60 镜一次输出易截断）② 参考图编号 `Image N` 由工作台自动拼还是让 DeepSeek 写 ③ 生成后自动落库建镜头 vs 预览确认后再落。
"""
with io.open(LOG, "a", encoding="utf-8") as f:
    f.write(add)
print("日志已追加，现", len(io.open(LOG, encoding="utf-8").read()), "chars")
print("tools/:", sorted(n for n in os.listdir(os.path.join(ROOT, "tools"))))
