"""一次性补丁：shot_service.py 里删就绪态/候选输出，任务态改带失败字段。"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:/Aicomfyui/短剧工作台/backend/app/services/shot_service.py")
t = P.read_text(encoding="utf-8")


def expect(old: str, new: str, label: str) -> None:
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"✗ {label}: 命中 {n} 次（应为 1），未写回")
    t = t.replace(old, new, 1)
    print(f"  ✓ {label}")


# 1) 批量任务查询带上失败字段（出图/出视频两列都要用）
expect(
    '        """SELECT l.target_id AS shot_id, t.status, t.task_kind, t.progress, t.id\n'
    "           FROM generation_tasks t JOIN task_links l ON l.task_id=t.id\n"
    '           WHERE l.target_kind=\'shot\' AND l.target_id IN ({ph})""", ids)\n',
    '        """SELECT l.target_id AS shot_id, t.status, t.task_kind, t.progress, t.id,\n'
    "                  t.fail_kind, t.fail_message, t.error,\n"
    "                  t.queued_at, t.started_at, t.finished_at\n"
    "           FROM generation_tasks t JOIN task_links l ON l.task_id=t.id\n"
    '           WHERE l.target_kind=\'shot\' AND l.target_id IN ({ph})""", ids)\n',
    "批量任务查询补失败字段",
)

# 2) 删「待确认候选数」统计
expect(
    "    # 待确认候选数\n"
    "    cand = {}\n"
    "    for part in _chunks(ids):\n"
    "        for r in db.query(\n"
    '            """SELECT shot_id, COUNT(*) AS c FROM shot_candidates\n'
    "               WHERE candidate_status='pending' AND shot_id IN (%s) GROUP BY shot_id\"\"\"\n"
    '                % _placeholders(len(part)), tuple(part)):\n'
    '            cand[r["shot_id"]] = r["c"]\n'
    "\n",
    "",
    "删待确认候选统计",
)

# 3) 输出里删 readiness
expect(
    '                "readiness": s["readiness"],\n',
    "",
    "list_shots 输出 readiness",
)

# 4) 输出里删 pending_candidates
expect(
    '                "pending_candidates": cand.get(sid, 0),\n',
    "",
    "list_shots 输出 pending_candidates",
)

# 5) get_shot 里删 candidates
expect(
    '        "candidates": db.query("SELECT * FROM shot_candidates WHERE shot_id=?", (shot_id,)),\n',
    "",
    "get_shot 输出 candidates",
)

P.write_text(t, encoding="utf-8")
for kw in ("readiness", "candidate", "confirmed_at"):
    hits = t.count(kw)
    print(f"残留 {kw}: {hits}")
print("OK")
