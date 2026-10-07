import sqlite3, os

base = r"D:\Aicomfyui\短剧工作台"

# 1) 迁移运行库：给 shot_details 加 assets_text 列
dbp = os.path.join(base, "data", "studio.db")
conn = sqlite3.connect(dbp, timeout=30)
cur = conn.cursor()
cols = [r[1] for r in cur.execute("PRAGMA table_info(shot_details)")]
print("shot_details cols before:", cols)
if "assets_text" not in cols:
    cur.execute("ALTER TABLE shot_details ADD COLUMN assets_text TEXT")
    conn.commit()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(shot_details)")]
    print("after ALTER:", cols)
else:
    print("assets_text already exists, skip ALTER")
conn.close()

# 2) schema.sql 同步加列（用于后续新建库）
sp = os.path.join(base, "backend", "app", "core", "schema.sql")
b = open(sp, "rb").read()
anchor = "  action_beats        TEXT,".encode("utf-8")
assert b.count(anchor) == 1, ("anchor count", b.count(anchor))
ins = ("  assets_text         TEXT,                    -- "
       "本镜出场资产中文名（创作期记录，不卡资产库）\r\n").encode("utf-8")
b2 = b.replace(anchor, ins + anchor, 1)
open(sp, "wb").write(b2)
print("schema.sql patched, action_beats anchors left:", b2.count(anchor))
