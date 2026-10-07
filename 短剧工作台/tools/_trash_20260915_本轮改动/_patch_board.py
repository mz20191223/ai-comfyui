"""看板：删就绪态列/筛选器，任务态拆成「出图」「出视频」两列。"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:/Aicomfyui/短剧工作台/frontend/src/views/ShotBoard.vue")
t = P.read_text(encoding="utf-8")


def one(old: str, new: str, label: str) -> None:
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"✗ {label}: 命中 {n} 次（应为 1），未写回")
    t = t.replace(old, new, 1)
    print(f"  ✓ {label}")


# 1) 就绪态筛选器
one(
    '        <el-select v-model="filterReady" size="small" style="width: 118px" clearable placeholder="就绪态">\n'
    "          <el-option v-for=\"r in ['ready', 'pending_confirm', 'draft']\" :key=\"r\" :label=\"readyLabel(r)\" :value=\"r\" />\n"
    "        </el-select>\n",
    "",
    "删就绪态筛选器",
)

# 2) 就绪态列 + 任务态列 → 出图 / 出视频
one(
    '        <el-table-column label="就绪态" width="96">\n'
    '          <template #default="{ row }">\n'
    '            <span class="pill" :class="readyClass(row.readiness)">{{ readyLabel(row.readiness) }}</span>\n'
    '            <div v-if="row.pending_candidates" class="tiny muted">待确认 {{ row.pending_candidates }}</div>\n'
    "          </template>\n"
    "        </el-table-column>\n"
    '        <el-table-column label="任务态" width="90">\n'
    '          <template #default="{ row }">\n'
    '            <span v-if="row.task_state.has_running" class="pill run">\n'
    '              <span class="dot run"></span>{{ row.task_state.max_progress }}%\n'
    "            </span>\n"
    '            <span v-else-if="row.task_state.has_failed" class="pill err">失败</span>\n'
    '            <span v-else-if="row.status.has_video" class="pill ok">已出片</span>\n'
    '            <span v-else class="muted tiny">—</span>\n'
    "          </template>\n"
    "        </el-table-column>\n",
    '        <el-table-column label="出图" width="96">\n'
    '          <template #default="{ row }">\n'
    "            <TaskPill :slot=\"row.task_state.image\" />\n"
    "          </template>\n"
    "        </el-table-column>\n"
    '        <el-table-column label="出视频" width="96">\n'
    '          <template #default="{ row }">\n'
    "            <TaskPill :slot=\"row.task_state.video\" />\n"
    "          </template>\n"
    "        </el-table-column>\n",
    "任务态拆两列",
)

# 3) script：导入组件
one(
    "import { api, thumbUrl } from '../api'\n",
    "import { api, thumbUrl } from '../api'\n"
    "import TaskPill from '../components/TaskPill.vue'\n",
    "导入 TaskPill",
)

# 4) 删 filterReady
one("const filterReady = ref('')\n", "", "删 filterReady 变量")
one(
    "    if (filterReady.value && s.readiness !== filterReady.value) return false\n",
    "",
    "删就绪态过滤",
)

# 5) 删 readyLabel / readyClass，rowClass 改看任务态
one(
    "function readyLabel(r) {\n"
    "  return { ready: '就绪', pending_confirm: '待确认', draft: '草稿', extracting: '解析中' }[r] || r\n"
    "}\n"
    "function readyClass(r) {\n"
    "  return { ready: 'ok', pending_confirm: 'warn', draft: 'gray', extracting: 'run' }[r] || 'gray'\n"
    "}\n"
    "function rowClass({ row }) {\n"
    "  return row.readiness === 'pending_confirm' ? 'row-warn' : ''\n"
    "}\n",
    "function rowClass({ row }) {\n"
    "  const a = row.task_state.image\n"
    "  const b = row.task_state.video\n"
    "  return a?.status === 'failed' || b?.status === 'failed' ? 'row-err' : ''\n"
    "}\n",
    "rowClass 改任务态",
)

P.write_text(t, encoding="utf-8")
for kw in ("readiness", "readyLabel", "readyClass", "filterReady", "pending_candidates"):
    print(f"残留 {kw}: {t.count(kw)}")
