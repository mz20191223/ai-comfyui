# -*- coding: utf-8 -*-
"""14d-1 补角色身份锚点：md + DB(video_prompt) + 工作台视频侧引用
   —— 根因：视频侧只有首帧、无任何角色形态锚点 -> H3 自编成“赤裸肌肉人形”
"""
import os, re, shutil, sqlite3, sys

MD   = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"
DB   = r"D:\Aicomfyui\短剧工作台\data\studio.db"
SHOT = 114          # 14d-1
CHAR = "权限魅影_角色参考图.jpg"

md = open(MD, encoding="utf-8").read()
NL = "\r\n" if "\r\n" in md else "\n"
print("md newline:", repr(NL), "| len:", len(md))

# ---------- 定位 14d-1 小节 ----------
i1 = md.index("## 镜头14d-1")
i2 = md.index("## 镜头14d-2")
sec = md[i1:i2]
print("14d-1 小节长度:", len(sec))

# ---------- DB 取当前 vp ----------
con = sqlite3.connect(DB); cur = con.cursor()
cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=?", (SHOT,))
vp = cur.fetchone()[0]
print("vp len(before):", len(vp))

# ================= 编辑定义 =================
NEW_PIC2 = ("Picture 2：" + CHAR + " — 角色身份锚点（**形态参考·非首帧**）：全片魅影的形态与质感严格以图中「MAIN FORM」的权限魅影为唯一依据"
            "——暗色雾质人形、半透明、整个身体由烟雾构成、面部隐于暗色雾中只露一双紫色发光瞳仁、无嘴、体态修长（非健美肌肉体型）；"
            "本图**只提供「角色本体长什么样」**（形态/质感/瞳色）；画面内容、构图、光线与运镜一律以 Picture 1 与下方时序为准；"
            "图内的分格排版、色卡、蓝色图标与标题文字均属设定板版式、与角色本体无关")
NEW_CONSIST = ("⚠️ 角色一致性（Picture 1 与 Picture 2 为同一人）：魅影在本片自始至终是 Picture 2 那位"
               "——同一副暗色雾质人形躯体、同一双紫色发光瞳仁、同样无嘴、同样修长体态、通体由雾构成且边缘持续消散；"
               "从首帧到片尾是同一个角色，形态与质感保持稳定")

NEW_REFIMG1 = ("- ref_image_1: " + CHAR + "（**角色身份锚点·形态参考**：全片魅影的形态/质感/瞳色以此为唯一依据"
               "——暗色雾质人形、半透明、身体由雾构成、面部隐于暗雾只露一双紫色发光瞳仁、无嘴、体态修长；"
               "只取角色本体（形态/质感/瞳色），设定板的分格、色卡、图标、标题文字与图中缠绕的具象雾丝都不属于角色本体）")

NEW_SHOT1_INS = "、**形态与质感严格对齐 Picture 2 的权限魅影（同一副暗色雾质人形躯体、同一双紫色发光瞳仁、无嘴、修长体态）**"

NEW_NOTE = ("> 🎭 **2026-09-24 角色身份锚点补录（用户决策）**：本轮出片雾已分层成功（不粘人），但魅影漂成「赤裸肌肉人形」"
            "——根因＝视频侧**只有首帧、没有任何角色身份锚点**（角色图原先只挂 image 侧，不进 H3 请求）。"
            "故补挂视频侧 slot1＝`" + CHAR + "`（**无嘴版**，08-24；新版 `权限魅影_角色参考图新.jpg` 有獠牙不可用）作形态锚点，"
            "写成 Picture 2 / ref_image_1，并在提示词里加「角色一致性」段锁形态。"
            "该图是拼贴设定板，故声明中写明「只取角色本体，不取分格/色卡/图标/文字/缠绕雾丝」。")

def edit(txt, tag):
    """对一段文本（md 小节 或 vp）做同一组编辑，返回新文本"""
    out = txt
    # E1 灰白雾态 -> 暗色雾质（仅指魅影本体，环境雾仍为灰白冷雾）
    n1 = out.count("半透明灰白雾态")
    assert n1 >= 1, f"[{tag}] 未找到『半透明灰白雾态』"
    out = out.replace("半透明灰白雾态", "半透明暗色雾质")
    # E2 在 Picture 1 行后插入 Picture 2 + 角色一致性
    m = re.search(r"^Picture 1：0114d不带雾\.jpg.*$", out, re.M)
    assert m, f"[{tag}] 未找到 Picture 1 行"
    ins = NL + NEW_PIC2 + NL + NEW_CONSIST
    out = out[:m.end()] + ins + out[m.end():]
    # E3 [Shot 1] 行插入形态对齐句
    n3 = out.count("占据画面主体")
    assert n3 >= 1, f"[{tag}] 未找到『占据画面主体』"
    assert out.count("占据画面主体，雾态身形") >= 1 or "占据画面主体、" in out, f"[{tag}] 锚点上下文异常"
    out = out.replace("占据画面主体，雾态身形", "占据画面主体" + NEW_SHOT1_INS + "，雾态身形")
    # E4 ref_image_0 行后插入 ref_image_1
    m4 = re.search(r"^- ref_image_0:.*$", out, re.M)
    assert m4, f"[{tag}] 未找到 ref_image_0 行"
    out = out[:m4.end()] + NL + NEW_REFIMG1 + out[m4.end():]
    print(f"[{tag}] 灰白雾态替换 {n1} 处 | 段落增长 {len(out)-len(txt)} 字")
    return out

# ---- 先全部在内存里算好、断言通过再落盘 ----
md2 = edit(sec, "md")
vp2 = edit(vp, "vp")

# ---- md 专属：工作流注释块补记本次决策（不进模型）----
mnote = re.search(r"^> 💡 \*\*2026-09-24 雾处理定案·派戏版（终版）\*\*.*$", md2, re.M)
assert mnote, "未找到 雾处理定案 注释行"
md2 = md2[:mnote.end()] + NL + NEW_NOTE + md2[mnote.end():]
assert NEW_NOTE in md2 and md2.count("角色身份锚点补录") == 1
print("md 注释块补记完成")

# 追加 ⚠️ 角色一致性 的复核
for tag, t in (("md", md2), ("vp", vp2)):
    assert NEW_PIC2 in t and NEW_CONSIST in t, f"[{tag}] 新行缺失"
    assert t.count("Picture 2：") == 1, f"[{tag}] Picture 2 计数异常: {t.count('Picture 2：')}"
    assert t.count("ref_image_1: " + CHAR) == 1, f"[{tag}] ref_image_1 计数异常"
    assert "半透明灰白雾态" not in t, f"[{tag}] 旧口径残留"
    assert NEW_SHOT1_INS in t, f"[{tag}] [Shot 1] 插入失败"

# DB 复核：vp 目标计数
assert vp2.count("Picture 2：") == 1 and vp2.count("角色一致性") == 1

# ---- 备份 ----
shutil.copy(MD, MD + ".bak-20260924-charref")
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
shutil.copy(DB, DB + ".bak-20260924-charref")
print("备份完成")

# ---- 落盘 md（替换小节）----
md_new = md[:i1] + md2 + md[i2:]
open(MD, "w", encoding="utf-8", newline="").write(md_new)
print("md 已写入, len:", len(md_new))

# ---- 落盘 DB：vp + 视频侧角色锚点链接 ----
cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=?", (vp2, SHOT))
print("vp 更新行数:", cur.rowcount, "| vp len(after):", len(vp2))

cur.execute("SELECT id,slot_index,role,file_name FROM shot_asset_links WHERE shot_id=? AND target_side='video' ORDER BY slot_index", (SHOT,))
print("更新前 video 侧:", cur.fetchall())

take = ("只取角色本体（暗色雾质人形/半透明/修长体态/一双紫色发光瞳仁/无嘴）；"
        "不取拼贴分格、色卡、蓝色图标、标题文字；不取图中缠绕的具象雾丝（雾由模型生成）")
cur.execute("""INSERT INTO shot_asset_links (shot_id, target_side, slot_index, role, file_name, take_note, ref_version)
               VALUES (?, 'video', 1, '形态锚点', ?, ?, 'concept')""", (SHOT, CHAR, take))
print("新增 link id:", cur.lastrowid)
con.commit()

# ---- 终态校验 ----
cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=?", (SHOT,))
vp_chk = cur.fetchone()[0]
cur.execute("SELECT slot_index,role,file_name FROM shot_asset_links WHERE shot_id=? AND target_side='video' ORDER BY slot_index", (SHOT,))
links = cur.fetchall()
cur.execute("SELECT frame_type,file_name FROM shot_frames WHERE shot_id=? AND is_active=1", (SHOT,))
frames = cur.fetchall()
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()

print("\n=== 终态 ===")
print("video links:", links)
print("frames:", frames)
assert [r[0] for r in links] == list(range(len(links))), "slot 不连续"
assert links[0][2] == "0114d不带雾.jpg", "slot0 应为无雾首帧"
assert links[1][2] == CHAR, "slot1 应为权限魅影角色锚点"
assert vp_chk == vp2, "DB vp 与预期不一致"

# md 落盘后回读，逐字比对 vp 段
md_back = open(MD, encoding="utf-8").read()
s1 = md_back.index("## 镜头14d-1"); e1 = md_back.index("## 镜头14d-2")
secb = md_back[s1:e1]
k = secb.index("**API prompt（接口A·多图，I2VA）：**")
vp_from_md = secb[k:].rstrip()
vp_from_md = re.sub(r"(\r?\n)?---\s*$", "", vp_from_md).rstrip()
print("md 抽取 vp len:", len(vp_from_md), "| DB vp len:", len(vp_chk))
if vp_from_md != vp_chk:
    a = vp_from_md.splitlines(); b = vp_chk.splitlines()
    print("!! 不一致，逐行比对：")
    for n in range(max(len(a), len(b))):
        x = a[n] if n < len(a) else "<无>"
        y = b[n] if n < len(b) else "<无>"
        if x != y:
            print(f"  L{n+1}\n   md: {x[:160]}\n   db: {y[:160]}")
    sys.exit(1)
print("\n✅ md ↔ DB video_prompt 逐字一致；视频侧 ref 顺序 = ref_image_0(无雾首帧) / ref_image_1(权限魅影形态锚点)")
