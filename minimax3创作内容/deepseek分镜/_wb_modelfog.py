# -*- coding: utf-8 -*-
import re, sqlite3, shutil, os, datetime

MD = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"
DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"
TS = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

shutil.copy(MD, MD + f".bak-{TS}-modelfog")
shutil.copy(DB, DB + f".bak-{TS}-modelfog")
if os.path.exists(DB + ".wal"):
    shutil.copy(DB + ".wal", DB + ".wal" + f".bak-{TS}-modelfog")
print("backed up @", TS)

OLD_FEN = ("⚠️ 参考分工：人物与结构以 Picture 1（无雾）为准；雾气的形态与观感以 Picture 2（带雾）为参照目标。"
           "运动中——移动的是魅影本体，雾气是独立的大气层次、始终灵动飘散、不随人物刚性位移、不被当贴图冻结。")
NEW_FEN = ("⚠️ 雾气由模型生成：画面中的雾完全由模型自行生成，不依赖任何参考图；"
           "雾是独立的环境大气层次，始终灵动飘散、不随人物刚性位移、不被当贴图冻结。")

def global_edits(s):
    """删除带雾参考 + 重写分工 + 强化雾自生成。三个删除串只存在于 14d-1/14d-2，全局安全。"""
    s, n1 = re.subn(r'.*Picture 2：0114b2_tail.jpg — 雾气观感参考（非首帧·带雾）.*\r?\n', '', s)
    assert n1 == 2, f"Picture2 删除数={n1}"
    assert s.count(OLD_FEN) == 2, f"参考分工数={s.count(OLD_FEN)}"
    s = s.replace(OLD_FEN, NEW_FEN)
    s, n3 = re.subn(r'.*ref_image_1: 0114b2_tail.jpg（\*\*雾气观感参考·带雾·非首帧\*\*.*\r?\n', '', s)
    assert n3 == 2, f"ref_image_1 删除数={n3}"
    s = s.replace("四周黑雾持续翻涌、飘移、动态流动，雾丝随",
                  "四周黑雾（由模型生成）持续翻涌、飘移、动态流动，雾丝随")
    return s

def renumber(s):
    """14d-2 重编号。调用方必须保证 s 只含 14d-2 作用域（md 需切节；DB vp 本身单镜安全）。"""
    s = s.replace("Picture 3：", "Picture 2：").replace("Picture 4：", "Picture 3：").replace("Picture 5：", "Picture 4：")
    s = s.replace("（Picture 3）", "（Picture 2）").replace("（Picture 4，", "（Picture 3，")
    s = s.replace("ref_image_2: 死循环妖", "ref_image_1: 死循环妖")\
         .replace("ref_image_3: 0110_tail", "ref_image_2: 0110_tail")\
         .replace("ref_image_4: 公司办公室", "ref_image_3: 公司办公室")
    return s

# ---- md：全局编辑 + 仅 14d-2 节内重编号 ----
s = open(MD, encoding="utf-8").read()
s = global_edits(s)
start = s.index("## 镜头14d-2")
nxt = s.find("\n## 镜头", start + 1)
nxt = len(s) if nxt == -1 else nxt
mid = renumber(s[start:nxt])
s2 = s[:start] + mid + s[nxt:]

assert s2.count("ref_image_1: 死循环妖") == 2   # 12a 原有 1 + 14d-2 改后 1
assert s2.count("ref_image_3: 公司办公室") == 3  # 14c/22镜 原有 2 + 14d-2 改后 1
assert s2.count("ref_image_4: 公司办公室") == 1  # 14a-2 未被误伤
assert s2.count("ref_image_2: 0110_tail") == 3  # 17/21镜 原有 2 + 14d-2 改后 1
assert s2.count("ref_image_3: 0110_tail") == 0
assert s2.count("Picture 2：") == 1
assert s2.count("（Picture 2）") == 1
assert s2.count("（Picture 3，") == 1
assert s2.count("（由模型生成）") >= 2
# 顺手更正 14d-2 工作流注释里过时的首帧说明
old_note = "**首帧改用 0114b2_tail.jpg**（承接 14b-2 尾帧、与 14d-1 同源；0114d.jpg 已移入废弃内容）"
new_note = "**首帧改用 0114d不带雾.jpg**（2026-09-24 双参考证伪：带雾参考图被 H3 当凝固贴图附着角色；改为仅无雾首帧，雾全由模型自生成）"
assert s2.count(old_note) == 1
s2 = s2.replace(old_note, new_note)
assert s2.count("0114b2_tail.jpg") == 1   # 仅剩 14b-2 自身段落描述（1059行），14d 双镜已清零
open(MD, "w", encoding="utf-8").write(s2)
print("MD edited OK")

# ---- DB：vp 本身是单镜文本，全局编辑 + 重编号均安全 ----
con = sqlite3.connect(DB); cur = con.cursor()
for sid in (114, 182):
    cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=?", (sid,))
    vp = cur.fetchone()[0]
    assert vp, f"shot {sid} vp empty"
    vp2 = renumber(global_edits(vp))
    assert "ref_image_1: 0114b2_tail" not in vp2
    assert "Picture 2：0114b2_tail" not in vp2
    assert "0114b2_tail.jpg" not in vp2
    cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=?", (vp2, sid))
    print(f"DB vp shot {sid} synced, new_len={len(vp2)}")
con.commit()

# ---- 工作台引用链接：删带雾参考(slot1)，14d-2 重编号 ----
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
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()
print("\nALL DONE")
