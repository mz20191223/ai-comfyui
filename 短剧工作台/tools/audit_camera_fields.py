# -*- coding: utf-8 -*-
"""盘点所有镜头的景别/视角/运镜填写情况。"""
import sqlite3
from pathlib import Path

c = sqlite3.connect(r"D:/Aicomfyui/短剧工作台/data/studio.db")
c.row_factory = sqlite3.Row

for ep in c.execute("SELECT id, number, title FROM episodes ORDER BY id"):
    print("=" * 78)
    print(f"第{ep['number']}集  (episode_id={ep['id']})  {ep['title']}")
    print("=" * 78)
    rows = c.execute("""
        SELECT s.id, s.shot_code, s.title, s.sort_order, s.readiness,
               d.camera_shot, d.angle, d.movement, d.subject_position, d.camera_note
        FROM shots s LEFT JOIN shot_details d ON d.shot_id = s.id
        WHERE s.episode_id = ? ORDER BY s.sort_order, s.id
    """, (ep["id"],)).fetchall()
    filled = empty = 0
    for r in rows:
        has = any([r["camera_shot"], r["angle"], r["movement"]])
        filled += int(bool(has))
        empty += int(not has)
        mark = "●" if has else "○"
        print(f" {mark} id={r['id']:<4} {str(r['shot_code']):<10} {str(r['title'] or '')[:16]:<18}"
              f" 景别={r['camera_shot'] or '-':<5} 视角={r['angle'] or '-':<13}"
              f" 运镜={r['movement'] or '-':<11} 位置={r['subject_position'] or '-'}")
    print(f"\n  已填 {filled} / 空 {empty} / 共 {len(rows)}")
