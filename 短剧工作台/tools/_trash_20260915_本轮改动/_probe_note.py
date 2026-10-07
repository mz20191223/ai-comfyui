# -*- coding: utf-8 -*-
"""临时探针 v2：确认 wiz_*_note 是否逐字出现在 image_prompt / video_prompt 正文里。"""
import sqlite3, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

db = r"D:\Aicomfyui\短剧工作台\data\studio.db"
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row

rows = con.execute(
    "SELECT shot_id, image_prompt, video_prompt, wiz_image_note, wiz_video_note "
    "FROM shot_details ORDER BY shot_id"
).fetchall()

any_note = 0
hit = 0
for r in rows:
    for kind, note, body in (
        ("image", r["wiz_image_note"], r["image_prompt"]),
        ("video", r["wiz_video_note"], r["video_prompt"]),
    ):
        note = (note or "").strip()
        if not note:
            continue
        any_note += 1
        body = body or ""
        ok = note in body
        if ok:
            hit += 1
        print(
            f"shot {r['shot_id']} [{kind}] note_len={len(note)} in_body={ok} body_len={len(body)}"
        )
        if not ok:
            print("    note:", note[:80])
            print("    body_has_prefix:", note[:10] in body)

print("---")
print("带 note 的槽位:", any_note, " 逐字命中正文:", hit)
print("总镜头明细行数:", len(rows))
