# -*- coding: utf-8 -*-
"""看一眼真实的 image_prompt / video_prompt 结构，决定注入位置。"""
import sqlite3
from pathlib import Path

db = Path(r"D:/Aicomfyui/短剧工作台/data/studio.db")
conn = sqlite3.connect(str(db))
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT s.shot_code, d.image_prompt, d.video_prompt, d.video_prompt_prefix,
           d.camera_shot, d.angle, d.movement, d.subject_position, d.camera_note
    FROM shots s JOIN shot_details d ON d.shot_id = s.id
    WHERE (d.image_prompt IS NOT NULL AND TRIM(d.image_prompt) <> '')
       OR (d.video_prompt  IS NOT NULL AND TRIM(d.video_prompt)  <> '')
    ORDER BY s.id LIMIT 3
""").fetchall()

for r in rows:
    print("=" * 70)
    print("shot:", r["shot_code"], "| 景别/视角/运镜/位置:",
          r["camera_shot"], "/", r["angle"], "/", r["movement"], "/", r["subject_position"])
    print("--- camera_note:", repr(r["camera_note"])[:200])
    print("--- PREFIX:", (r["video_prompt_prefix"] or "")[:200])
    print("--- IMAGE_PROMPT ---")
    print((r["image_prompt"] or "")[:1400])
    print("--- VIDEO_PROMPT ---")
    print((r["video_prompt"] or "")[:1400])

cols = [c[1] for c in conn.execute("PRAGMA table_info(shot_details)").fetchall()]
print("\nshot_details 列:", cols)
