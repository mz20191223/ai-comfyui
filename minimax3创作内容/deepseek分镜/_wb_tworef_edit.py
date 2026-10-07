# -*- coding: utf-8 -*-
import sqlite3, os, shutil

MD = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"
DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"

# ---- 备份 ----
shutil.copy2(MD, MD + ".bak-20260924-tworef")
for ext in ("", "-wal", "-shm"):
    p = DB + ext
    if os.path.exists(p):
        shutil.copy2(p, p + ".bak-20260924-tworef")

with open(MD, "r", encoding="utf-8", newline="") as f:
    content = f.read()

lines = content.splitlines(keepends=True)

def find(sub, start=0):
    for i, l in enumerate(lines):
        if i >= start and sub in l:
            return i
    raise ValueError("NOT FOUND: " + sub)

h1 = find("## 镜头14d-1")
h2 = find("## 镜头14d-2")
h17 = find("## 镜头17")

# 行尾风格探测
endl = "\r\n" if lines[h1].endswith("\r\n") else "\n"

# ===== 14d-1 素材关系声明 (Picture1 + Picture2拼贴板 -> 无雾首帧 + 带雾风格) =====
i1 = find("Picture 1：0114b2_tail.jpg — 首帧锚点（0.00s）：承接 14b-2 尾帧，魅影为半透明灰白雾态人形、形态完整、面部偏暗、于画面纵深远处")
i2 = find("Picture 2：权限魅影_角色参考图.jpg — 魅影形态：雾态人形、面部隐于雾中只露一双紫色发光的瞳仁、无嘴、不开口")
block1 = [
 "Picture 1：0114d不带雾.jpg — 首帧锚点（0.00s）+ 人物/结构参考（无雾）：承接 14b-2 尾帧的无雾版本，魅影为半透明灰白雾态人形、形态完整、面部偏暗、于画面纵深远处（约18%画面高度、距镜头约4-5米）、双臂垂放、无嘴、不开口；以此为基础魅影自身向前缓缓飘移靠近镜头（镜头保持静止不动），由小变大至中近景，暗场办公室纵深随之虚化为背景，左右虚空全空、画面中无人物无妖",
 "Picture 2：0114b2_tail.jpg — 雾气观感参考（非首帧·带雾）：魅影周身应有的雾态与雾感仅作风格参照；视频中的雾须由模型自行生成、始终灵动飘散，不可直接搬用此图中凝固的雾丝",
 "⚠️ 参考分工：人物与结构以 Picture 1（无雾）为准；雾气的形态与观感以 Picture 2（带雾）为参照目标。运动中——移动的是魅影本体，雾气是独立的大气层次、始终灵动飘散、不随人物刚性位移、不被当贴图冻结。",
]

# ===== 14d-2 素材关系声明 (Picture1..5 -> 无雾首帧 + 带雾风格 + 顺移 + 删拼贴板) =====
j1 = find("Picture 1：0114b2_tail.jpg — 首帧锚点（0.00s）：承接 14b-2 尾帧，魅影为半透明灰白雾态人形、形态完整、双臂垂放的远景", h2)
j2 = find("Picture 5：权限魅影_角色参考图.jpg — 魅影形态：雾态人形、面部隐于雾中只露紫色发光瞳仁、无嘴、不开口", h2)
block2 = [
 "Picture 1：0114d不带雾.jpg — 首帧锚点（0.00s）+ 人物/结构参考（无雾）：承接 14b-2 尾帧的无雾版本，魅影为半透明灰白雾态人形、形态完整、双臂垂放的远景，镜头保持静止、魅影自身向后缓缓飘移远离，背景为虚化暗场、工位剪影隐去、左右虚空全空、画面中无人物无妖",
 "Picture 2：0114b2_tail.jpg — 雾气观感参考（非首帧·带雾）：魅影周身应有的雾态与雾感仅作风格参照；视频中的雾须由模型自行生成、始终灵动飘散，不可直接搬用此图中凝固的雾丝",
 "⚠️ 参考分工：人物与结构以 Picture 1（无雾）为准；雾气的形态与观感以 Picture 2（带雾）为参照目标。运动中——移动的是魅影本体，雾气是独立的大气层次、始终灵动飘散、不随人物刚性位移、不被当贴图冻结。",
 "Picture 3：死循环妖_角色参考图.jpg — 死循环妖形态：黑发束髻、深色长袍、青色双环发光眼、绿色能量质感",
 "Picture 4：0110_tail.jpg — 内存黑洞王形态：仅取巨大体型与暗色质感（严禁带入其中的过客与红色警示屏）",
 "Picture 5：公司办公室_场景参考图.jpg — 仅作熄灯办公区的暗调氛围参考",
]

# ===== 14d-1 API参数 ref_image_0/1 =====
c0 = find("- ref_image_0: 0114b2_tail.jpg（**首帧锚点·承接 14b-2 尾帧**")
c1 = find("- ref_image_1: 权限魅影_角色参考图.jpg（魅影**形态锚点**", h1)
ref1 = [
 "- ref_image_0: 0114d不带雾.jpg（**首帧锚点·人物结构参考·无雾**：承接 14b-2 尾帧的无雾版本，魅影半透明灰白雾态、形态完整、面部偏暗、于画面纵深远处双臂垂放、无嘴不开口；镜头保持静止、魅影自身向前飘移靠近至中近景、暗场办公室纵深虚化为背景、左右两侧虚空全空、无过客无妖）",
 "- ref_image_1: 0114b2_tail.jpg（**雾气观感参考·带雾·非首帧**：魅影周身应有的雾态与雾感仅作风格参照；视频中的雾由模型自生成、始终灵动飘散，不可直接搬用此图凝固雾丝）",
]

# ===== 14d-2 API参数 ref_image_0..4 =====
h0 = find("- ref_image_0: 0114b2_tail.jpg（**首帧锚点·承接 14b-2 尾帧**", h2)
h4 = find("- ref_image_4: 权限魅影_角色参考图.jpg（魅影**形态锚点**", h2)
ref2 = [
 "- ref_image_0: 0114d不带雾.jpg（**首帧锚点·人物结构参考·无雾**：承接 14b-2 尾帧的无雾版本，魅影半透明灰白雾态、形态完整、双臂垂放的远景、镜头保持静止、魅影自身向后缓缓飘移远离、背景虚化暗场、工位剪影隐去、左右虚空全空、无过客无妖）",
 "- ref_image_1: 0114b2_tail.jpg（**雾气观感参考·带雾·非首帧**：魅影周身应有的雾态与雾感仅作风格参照；视频中的雾由模型自生成、始终灵动飘散，不可直接搬用此图凝固雾丝）",
 "- ref_image_2: 死循环妖_角色参考图.jpg（角色设定图——死循环妖形态锚点：**黑发束髻、深色长袍、青色双环发光眼**＋绿色能量质感；严禁拼贴排版与色值标注）",
 "- ref_image_3: 0110_tail.jpg（镜头10 视频尾帧——内存黑洞王形态锚点，**仅取形态/质感/色调/巨大体型**；**严禁带入其中的过客与红屏工位环境**）",
 "- ref_image_4: 公司办公室_场景参考图.jpg",
]

# ---- 先做单行子串替换（不改变行数，索引安全）----
b1 = find("以 Picture 1（0114b2_tail.jpg·承接 14b-2 尾帧）为起点", h1)
lines[b1] = lines[b1].replace("以 Picture 1（0114b2_tail.jpg·承接 14b-2 尾帧）为起点",
                              "以 Picture 1（0114d不带雾.jpg·承接 14b-2 尾帧的无雾版）为起点")
# 14d-2 的 [Shot 1] 原本没有"以 Picture 1 为起点"，显式补上无雾首帧锚点（与 14d-1 对齐）
e2 = find("[Shot 1] 竖屏 9:16，单一连续镜头（无转场、无黑场、无字幕）。镜头保持静止不动、魅影自身向后缓缓飘移远离镜头：", h2)
lines[e2] = lines[e2].replace(
    "[Shot 1] 竖屏 9:16，单一连续镜头（无转场、无黑场、无字幕）。镜头保持静止不动、魅影自身向后缓缓飘移远离镜头：",
    "[Shot 1] 竖屏 9:16，单一连续镜头（无转场、无黑场、无字幕）。以 Picture 1（0114d不带雾.jpg·承接 14b-2 尾帧的无雾版）为起点、镜头保持静止不动、魅影自身向后缓缓飘移远离镜头：")
f1 = find("左侧虚空中死循环妖（Picture 2）", h2)
lines[f1] = lines[f1].replace("（Picture 2）", "（Picture 3）")
g1 = find("右侧虚空中内存黑洞王（Picture 3，体型远大于魅影）", h2)
lines[g1] = lines[g1].replace("（Picture 3，体型远大于魅影）", "（Picture 4，体型远大于魅影）")

# ---- 再做区间替换（按起始索引降序，避免索引漂移）----
edits = [
    (i1, i2, block1),
    (c0, c1, ref1),
    (j1, j2, block2),
    (h0, h4, ref2),
]
edits.sort(key=lambda e: e[0], reverse=True)
for s, e, blk in edits:
    lines[s:e+1] = [l + endl for l in blk]

new_content = "".join(lines)

# ---- 抽取 vp（从改后 md 抽，保证 md↔DB 一致）----
def extract_vp(text, header, next_header):
    start = text.index(header)
    nxt = text.index(next_header, start + 5)
    block = text[start:nxt]
    api = block.index("**API prompt（接口A·多图，I2VA）：**")
    vp = block[api:]
    for sep in ("\n---\n", "\r\n---\r\n"):
        if sep in vp:
            vp = vp[:vp.rindex(sep)]
    vp = vp.rstrip("\n").rstrip("\r")
    return vp

vp1 = extract_vp(new_content, "## 镜头14d-1", "## 镜头14d-2")
vp2 = extract_vp(new_content, "## 镜头14d-2", "## 镜头17")

# ---- 断言 ----
assert new_content.count("0114d不带雾.jpg") >= 4, "无雾图引用数不足"
assert new_content.count("参考分工") >= 2, "分工说明缺失"
assert new_content.count("移动的是魅影本体") >= 2, "运动说明缺失"
assert "权限魅影_角色参考图.jpg" not in vp1, "14d-1 vp 仍含拼贴板"
assert "权限魅影_角色参考图.jpg" not in vp2, "14d-2 vp 仍含拼贴板"
assert "0114d.jpg" not in vp2, "14d-2 vp 仍含旧 0114d.jpg"
assert "0114d不带雾.jpg" in vp1 and "0114b2_tail.jpg" in vp1
assert "0114d不带雾.jpg" in vp2 and "0114b2_tail.jpg" in vp2

# ---- 写回 md ----
with open(MD, "w", encoding="utf-8", newline="") as f:
    f.write(new_content)

# ---- 写回 DB ----
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("SELECT id FROM shots WHERE shot_code='14d-1'")
id114 = cur.fetchone()[0]
cur.execute("SELECT id FROM shots WHERE shot_code='14d-2'")
id182 = cur.fetchone()[0]
cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=?", (vp1, id114))
cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=?", (vp2, id182))
con.commit()

# 回读校验
cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=?", (id114,))
db_vp1 = cur.fetchone()[0]
cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=?", (id182,))
db_vp2 = cur.fetchone()[0]
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()

assert db_vp1 == vp1, "DB vp1 回读不一致"
assert db_vp2 == vp2, "DB vp2 回读不一致"

print("OK: md+DB 双写完成")
print("14d-1 (shot %d) vp_len=%d, 无雾图出现%d次" % (id114, len(vp1), vp1.count("0114d不带雾.jpg")))
print("14d-2 (shot %d) vp_len=%d, 无雾图出现%d次" % (id182, len(vp2), vp2.count("0114d不带雾.jpg")))
print("vp1 含分工说明:", "参考分工" in vp1, "| vp2 含分工说明:", "参考分工" in vp2)
print("vp1 含拼贴板:", "权限魅影_角色参考图" in vp1, "| vp2 含拼贴板:", "权限魅影_角色参考图" in vp2)
