# -*- coding: utf-8 -*-
import sqlite3, os, shutil, datetime

DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"
IMG = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\0114d不带雾.jpg"
IMG_NAME = "0114d不带雾.jpg"
WITHFOG = "0114b2_tail.jpg"

# 备份
for ext in ("", "-wal", "-shm"):
    p = DB + ext
    if os.path.exists(p):
        shutil.copy2(p, p + ".bak-20260924-wire")

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys=OFF")
cur = con.cursor()

# 1) files 索引新图
cur.execute("SELECT id FROM files WHERE path=?", (IMG,))
if cur.fetchone() is None:
    cur.execute(
        "INSERT INTO files (path, file_name, ext, file_type, size_bytes, exists_flag, last_seen_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (IMG, IMG_NAME, ".jpg", "image", os.path.getsize(IMG), 1,
         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("files: 插入新图索引 id=", cur.lastrowid)
else:
    print("files: 已存在，跳过插入")

# 2) 两镜首帧改为无雾图
for fid in (152, 153):
    cur.execute("UPDATE shot_frames SET file_path=?, file_name=? WHERE id=?",
                (IMG, IMG_NAME, fid))
print("shot_frames.first: 已更新为", IMG_NAME)

# 3) 视频侧参考链接重排
# 14d-1 (shot 114): video 侧 slot0 + slot4
cur.execute("UPDATE shot_asset_links SET file_name=? WHERE id=2210", (IMG_NAME,))          # slot0 首帧锚点
cur.execute("UPDATE shot_asset_links SET file_name=?, role=? WHERE id=2214", (WITHFOG, "雾风格参考"))  # slot4 -> 带雾风格
# 14d-2 (shot 182): video 侧 slot0..4
cur.execute("UPDATE shot_asset_links SET file_name=? WHERE id=2739", (IMG_NAME,))                       # slot0 首帧锚点
cur.execute("UPDATE shot_asset_links SET file_name=?, role=? WHERE id=2740", (WITHFOG, "雾风格参考"))    # slot1 -> 带雾风格
cur.execute("UPDATE shot_asset_links SET file_name=? WHERE id=2741", ("死循环妖_角色参考图.jpg",))        # slot2 -> 死循环妖
cur.execute("UPDATE shot_asset_links SET file_name=? WHERE id=2742", ("0110_tail.jpg",))                 # slot3 -> 0110_tail
cur.execute("UPDATE shot_asset_links SET file_name=?, role=? WHERE id=2743", ("公司办公室_场景参考图.jpg", "环境参考"))  # slot4 -> 公司办公室
print("shot_asset_links: 视频侧链接已重排")

con.commit()

# ---- 回读校验 ----
def video_refs(sid):
    cur.execute("SELECT shot_code FROM shots WHERE id=?", (sid,)); code = cur.fetchone()[0]
    cur.execute("SELECT frame_type,file_name FROM shot_frames WHERE shot_id=? AND frame_type='first'", (sid,))
    first = cur.fetchone()
    cur.execute("SELECT slot_index,file_name,role FROM shot_asset_links WHERE shot_id=? AND target_side='video' ORDER BY slot_index", (sid,))
    links = cur.fetchall()
    return code, first, links

print("\n=== 校验 14d-1 (114) ===")
code, first, links = video_refs(114)
print("  first frame:", first[1])
print("  video refs:")
for s, fn, role in links:
    print(f"    slot{s}: {fn} ({role})")
assert first[1] == IMG_NAME, "14d-1 首帧未更新"
refs114 = [fn for _, fn, _ in links]
assert refs114[0] == IMG_NAME, "14d-1 ref_image_0 非无雾图"
assert refs114[1] == WITHFOG, "14d-1 ref_image_1 非带雾图"
assert all("权限魅影_角色参考图" not in fn for fn in refs114), "14d-1 仍含拼贴板"

print("\n=== 校验 14d-2 (182) ===")
code, first, links = video_refs(182)
print("  first frame:", first[1])
print("  video refs:")
for s, fn, role in links:
    print(f"    slot{s}: {fn} ({role})")
assert first[1] == IMG_NAME, "14d-2 首帧未更新"
refs182 = [fn for _, fn, _ in links]
expect182 = [IMG_NAME, WITHFOG, "死循环妖_角色参考图.jpg", "0110_tail.jpg", "公司办公室_场景参考图.jpg"]
assert refs182 == expect182, f"14d-2 refs 不符: {refs182}"
assert all("权限魅影_角色参考图" not in fn for fn in refs182), "14d-2 仍含拼贴板"

con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()
print("\nOK: 工作台接线完成，WAL 已回写主库")
