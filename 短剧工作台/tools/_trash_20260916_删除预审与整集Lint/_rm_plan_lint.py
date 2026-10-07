# -*- coding: utf-8 -*-
"""移除「生成方案预审」与「整集 Lint」两个功能（用户明确不需要）。

保留：单镜 Lint（shots.py /shots/{id}/lint + LintPanel.vue）、Lint 规则管理（PromptCenter + /lint-rules）。
所有删除均带内容断言，行号对不上就报错不动文件。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"D:\Aicomfyui\短剧工作台"


def read_lines(path):
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        return f.readlines()


def write_lines(path, lines):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)


def cut(path, spans, expect):
    """spans: [(from_1based, to_1based), ...] 闭区间；expect: {行号: 该行必须包含的子串}"""
    lines = read_lines(path)
    for ln, sub in expect.items():
        assert sub in lines[ln - 1], f"{os.path.basename(path)} L{ln} 断言失败：期望含 {sub!r}，实际 {lines[ln-1].rstrip()!r}"
    for a, b in spans:
        assert 1 <= a <= b <= len(lines), f"{os.path.basename(path)} 区间越界 {a}-{b} / 共 {len(lines)} 行"
    for a, b in sorted(spans, reverse=True):
        del lines[a - 1:b]
    write_lines(path, lines)
    return len(lines)


P = lambda *a: os.path.join(ROOT, *a)
report = []

# ---------------- 1. ShotBoard.vue ----------------
f = P("frontend", "src", "views", "ShotBoard.vue")
n = cut(
    f,
    [(14, 15), (86, 126), (166, 171), (215, 233)],
    {
        14: '生成方案预审',
        15: '整集 Lint',
        86: '',
        87: '<el-dialog v-model="showPlanDlg"',
        110: '整集 Lint 结果',
        126: '</el-dialog>',
        127: '',
        128: '镜头详情：弹窗内嵌',
        166: 'const showPlanDlg = ref(false)',
        171: 'const linting = ref(false)',
        172: 'const showDetail = ref(false)',
        215: 'async function showPlan()',
        225: 'async function lintAll()',
        233: '}',
        234: '',
        235: 'async function addShot()',
    },
)
report.append(("ShotBoard.vue", "删 4 段（2 按钮 / 2 弹窗 / 6 状态 / 2 函数）", n))

# ---------------- 2. Creation.vue ----------------
f = P("frontend", "src", "views", "Creation.vue")
n = cut(
    f,
    [(53, 53), (154, 177), (234, 236), (353, 357)],
    {
        53: 'openPlan(row)">生产方案',
        154: '',
        155: '<!-- 生产方案 -->',
        156: '生成方案预审',
        177: '</el-dialog>',
        178: '',
        179: '<!-- 创意编辑 -->',
        234: 'const planDlg = ref(false)',
        235: 'const planData = ref(null)',
        237: 'const ideaDlg = ref(false)',
        353: 'async function openPlan(ep)',
        358: 'function editIdea(row)',
    },
)
report.append(("Creation.vue", "删 4 段（1 按钮 / 1 弹窗 / 2 状态 / 1 函数）", n))

# ---------------- 3. api/index.js ----------------
f = P("frontend", "src", "api", "index.js")
n = cut(
    f,
    [(67, 67), (169, 169)],
    {
        66: 'lintShot:',
        67: 'lintEpisode:',
        68: 'generate:',
        168: 'pipeline:',
        169: 'productionPlan:',
        171: '// 时间轴与合成',
    },
)
report.append(("api/index.js", "删 lintEpisode / productionPlan", n))

# ---------------- 4. backend shots.py（整集 lint 路由） ----------------
f = P("backend", "app", "routers", "shots.py")
lines = read_lines(f)
idx = [i for i, l in enumerate(lines) if "def lint_episode(episode_id: int" in l]
assert len(idx) == 1, f"shots.py 中 lint_episode 定义数 = {len(idx)}"
i = idx[0]
assert '@router.post("/episodes/{episode_id}/lint")' in lines[i - 1], lines[i - 1]
assert "return lint_service.lint_episode" in lines[i + 1], lines[i + 1]
assert lines[i - 2].strip() == "" and lines[i - 3].strip() == "", "前置空行不符"
assert lines[i + 2].strip() == "" and lines[i + 3].strip() == "", "后置空行不符"
del lines[i - 2:i + 3]          # 含 2 前置空行 + 3 行函数体
assert '@router.post("/shots/{shot_id}/lint")' in "".join(lines), "单镜 lint 路由被误删！"
write_lines(f, lines)
report.append(("shots.py", "删 整集 lint 路由（保留单镜 lint）", len(lines)))

# ---------------- 5. backend creation.py（production-plan 是文件末函数） ----------------
f = P("backend", "app", "routers", "creation.py")
lines = read_lines(f)
idx = [i for i, l in enumerate(lines) if "def production_plan(episode_id: int" in l]
assert len(idx) == 1, f"creation.py 中 production_plan 定义数 = {len(idx)}"
i = idx[0]
assert lines[i - 3].startswith("# ---------------- 拍摄计划预审") or lines[i - 3].startswith(
    "# ---------------- 拍摄计划预审"
), lines[i - 3]
assert "批量生成前的预审" in lines[i + 1], lines[i + 1]
assert '@router.post("/episodes/{episode_id}/production-plan")' in lines[i - 1], lines[i - 1]
assert i + 2 == len(lines) - 1 or i + 2 <= len(lines), (i, len(lines))
keep = lines[:i - 3]            # 保留到「拍摄计划预审」注释前的最后一行
while keep and keep[-1].strip() == "":
    keep.pop()
if not keep[-1].endswith(("\n", "\r")):
    keep[-1] += "\n"
write_lines(f, keep)
assert "production_plan" not in "".join(read_lines(f)), "production_plan 仍有残留"
report.append(("creation.py", "删 production_plan 整段（文件末）", len(keep)))

print("=== 删除完成 ===")
for r in report:
    print("  %-16s %-42s -> %d 行" % r)
