# -*- coding: utf-8 -*-
"""导出指定镜头的判定依据：标题 / 概要 / 分镜图提示词 / 视频提示词正文。"""
import sqlite3
import sys

c = sqlite3.connect(r"D:/Aicomfyui/短剧工作台/data/studio.db")
c.row_factory = sqlite3.Row

lo = int(sys.argv[1]) if len(sys.argv) > 1 else 113
hi = int(sys.argv[2]) if len(sys.argv) > 2 else 121
LIM = int(sys.argv[3]) if len(sys.argv) > 3 else 700

rows = c.execute("""
    SELECT s.id, s.shot_code, s.title, s.notes, d.summary, d.action_beats, d.mood_tags,
           d.image_prompt, d.video_prompt, d.video_prompt_prefix, d.duration_sec, d.gen_mode,
           d.image_is_optional, d.image_target_name,
           (SELECT GROUP_CONCAT(role_name || ':' || text, ' | ')
              FROM shot_dialog_lines WHERE shot_id = s.id) AS lines
    FROM shots s LEFT JOIN shot_details d ON d.shot_id = s.id
    WHERE s.id BETWEEN ? AND ? ORDER BY s.sort_order, s.id
""", (lo, hi)).fetchall()

for r in rows:
    print("=" * 90)
    print(f"id={r['id']}  镜号={r['shot_code']}  时长={r['duration_sec']}  模式={r['gen_mode']}"
          f"  出图={not r['image_is_optional']}  目标={r['image_target_name']}")
    print(f"标题: {r['title']}")
    if r["notes"]:
        print(f"备注: {r['notes']}")
    print(f"概要: {r['summary']}")
    if r["action_beats"]:
        print(f"节拍: {r['action_beats']}")
    if r["lines"]:
        print(f"台词: {r['lines']}")
    print(f"\n-- 分镜图提示词 --\n{(r['image_prompt'] or '')[:LIM]}")
    print(f"\n-- 视频提示词 --\n{(r['video_prompt'] or '')[:LIM]}")
    print()
