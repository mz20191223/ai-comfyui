"""一次性补丁：TaskCenter.vue 任务态枚举对齐（pending → submitted，措辞统一）。"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:/Aicomfyui/短剧工作台/frontend/src/views/TaskCenter.vue")
t = P.read_text(encoding="utf-8")


def one(old: str, new: str, label: str) -> None:
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"✗ {label}: 命中 {n} 次（应为 1），未写回")
    t = t.replace(old, new, 1)
    print(f"  ✓ {label}")


one(
    "const STATUS = { pending: '排队', running: '进行中', succeeded: '成功', failed: '失败', cancelled: '已取消' }",
    "const STATUS = { submitted: '已提交', running: '进行中', succeeded: '已完成', failed: '失败', cancelled: '已取消' }",
    "STATUS 映射",
)
one(
    "(stats.value.by_status.running || 0) + (stats.value.by_status.pending || 0)",
    "(stats.value.by_status.running || 0) + (stats.value.by_status.submitted || 0)",
    "进行中卡片计数",
)
one(
    "  return { succeeded: 'ok', failed: 'err', running: 'run', pending: 'gray', cancelled: 'gray' }[s] || 'gray'",
    "  return { succeeded: 'ok', failed: 'err', running: 'run', submitted: 'gray', cancelled: 'gray' }[s] || 'gray'",
    "statusClass",
)

n = t.count("['pending', 'running']") + t.count("['running', 'pending']")
if n != 3:
    raise SystemExit(f"✗ 活跃态判定命中 {n} 次（应为 3），未写回")
t = t.replace("['pending', 'running']", "['submitted', 'running']")
t = t.replace("['running', 'pending']", "['running', 'submitted']")
print(f"  ✓ 活跃态判定 ×{n}")

P.write_text(t, encoding="utf-8")
print("残留 pending:", t.count("pending"))
