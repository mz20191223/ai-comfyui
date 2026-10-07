# -*- coding: utf-8 -*-
import re, sqlite3, shutil, os, datetime

DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"
TS = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy(DB, DB + f".bak-{TS}-modelfog2")
if os.path.exists(DB + ".wal"):
    shutil.copy(DB + ".wal", DB + ".wal" + f".bak-{TS}-modelfog2")
print("DB backed up @", TS)

OLD_FEN = ("⚠️ 参考分工：人物与结构以 Picture 1（无雾）为准；雾气的形态与观感以 Picture 2（带雾）为参照目标。"
           "运动中——移动的是魅影本体，雾气是独立的大气层次、始终灵动飘散、不随人物刚性位移、不被当贴图冻结。")
NEW_FEN = ("⚠️ 雾气由模型生成：画面中的雾完全由模型自行生成，不依赖任何参考图；"
           "雾是独立的环境大气层次，始终灵动飘散、不随人物刚性位移、不被当贴图冻结。")

def global_edits(s):
    s, n1 = re.subn(r'.*Picture 2：0114b2_tail.jpg — 雾气观感参考（非首帧·带雾）.*\r?\n', '', s)
    assert n1 == 1, f"Picture2 删除数={n1}"
    assert s.count(OLD_FEN) == 1
    s = s.replace(OLD_FEN, NEW_FEN)
    s, n3 = re.subn(r'.*ref_image_1: 0114b2_tail.jpg（\*\*雾气观感参考·带雾·非首帧\*\*.*\r?\n', '', s)
    assert n3 == 1, f"ref_image_1 删除数={n3}"
    s = s.replace("四周黑雾持续翻涌、飘移、动态流动，雾丝随",
                  "四周黑雾（由模型生成）持续翻涌、飘移、动态流动，雾丝随")
    return s

def renumber(s):
    s = s.replace("Picture 3：", "Picture 2：").replace("Picture 4：", "Picture 3：").replace("Picture 5：", "Picture 4：")
    s = s.replace("（Picture 3）", "（Picture 2）").replace("（Picture 4，", "（Picture 3，")
    s = s.replace("ref_image_2: 死循环妖", "ref_image_1: 死循环妖")\
         .replace("ref_image_3: 0110_tail", "ref_image_2: 0110_tail")\
         .replace("ref_image_4: 公司办公室", "ref_image_3: 公司办公室")
    return s

con = sqlite3.connect(DB); cur = con.cursor()
for sid in (114, 182):
    cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=?", (sid,))
    vp = cur.fetchone()[0]
    assert vp, f"shot {sid} vp empty"
    assert "0114b2_tail.jpg" in vp, f"shot {sid} vp 尚未同步（应含带雾参考）"
    vp2 = global_edits(vp)
    if sid == 182:
        vp2 = renumber(vp2)
    assert "0114b2_tail.jpg" not in vp2
    assert "雾气由模型生成" in vp2
    cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=?", (vp2, sid))
    print(f"DB vp shot {sid} synced, new_len={len(vp2)}")
con.commit()

cur.execute("DELETE FROM shot_asset_links WHERE shot_id=114 AND target_side='video' AND slot_index=1")
print("14d-1 删除 slot1 影响行:", cur.rowcount)
cur.execute("DELETE FROM shot_asset_links WHERE shot_id=182 AND target_side='video' AND slot_index=1")
print("14d-2 删除 slot1 影响行:", cur.rowcount)
cur.execute("UPDATE shot_asset_links SET slot_index = slot_index - 1 WHERE shot_id=182 AND target_side='video' AND slot_index > 1")
print("14d-2 重编号影响行:", cur.rowcount)
con.commit()

for sid in (114, 182):
    cur.execute("SELECT shot_code FROM shots WHERE id=?", (sid,)); code = cur.fetchone()[0]
    print(f"\n=== shot {sid} ({code}) video refs ===")
    cur.execute("SELECT slot_index,file_name,role FROM shot_asset_links WHERE shot_id=? AND target_side='video' ORDER BY slot_index", (sid,))
    for r in cur.fetchall():
        print("   ", r)
    cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=?", (sid,))
    vp = cur.fetchone()[0]
    print("   vp含分工说明:", "雾气由模型生成" in vp, "| vp含带雾图:", "0114b2_tail" in vp)
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()
print("\nALL DONE")
