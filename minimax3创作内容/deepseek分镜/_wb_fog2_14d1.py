# -*- coding: utf-8 -*-
import sqlite3, shutil, os, re

MD = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"
DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"

# 备份
shutil.copy(MD, MD + ".bak-20260924-fog2")
for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        shutil.copy(DB + ext, DB + ext + ".bak-20260924-fog2")

# 7 处替换：(旧, 新)
pairs = [
    # 1) 说明行
    ("⚠️ 雾气由模型生成：画面中的雾完全由模型自行生成，不依赖任何参考图；雾是独立的环境大气层次，始终灵动飘散、不随人物刚性位移、不被当贴图冻结。",
     "⚠️ 雾气由模型生成并独立“派戏”：画面中的雾完全由模型自行生成、不依赖任何参考图、更不与魅影黏为一体。雾分三层——①贴画面下缘的灰白冷雾自左向右缓缓横流；②魅影自身飘移时，半透明身形边缘不断剥离出细小雾丝、向后拖曳、拉长、消散（彗尾效应）；③偶有一缕薄雾自镜头前虚焦飘过、穿出画面。魅影核心比环境雾更实、略亮；环境雾更暗更稀，二者明确分层。"),

    # 2) [Shot 1] 整段雾句
    ("**四周黑雾（由模型生成）持续翻涌、飘移、动态流动，雾丝随细微气流不断变形，与魅影飘移形成纵深层次，雾气有独立生命、绝非静止贴图**",
     "**环境雾由模型生成、与魅影分层独立运动**：贴画面下缘的灰白冷雾自左向右缓缓横流；魅影自身飘移时，半透明身形边缘不断剥离出细小雾丝、向后拖曳、拉长、消散，形成流动的彗尾；偶有一缕薄雾自镜头前虚焦飘过、穿出画面，制造纵深；魅影核心比环境雾更实、略亮，环境雾更暗更稀，二者不黏连**"),

    # 3) 0.00–0.60s 雾句
    ("**四周黑雾（由模型生成）持续翻涌、飘移、动态流动，雾丝随气流不断变形，与魅影飘移形成纵深层次（雾有独立生命，不是贴图）**",
     "**贴画面下缘的灰白冷雾自左向右缓缓横流；魅影身形边缘开始剥离细小雾丝、向后拖曳消散，雾气有独立流动方向、不黏附角色、不是贴图**"),

    # 4) 0.60–3.30s 雾句
    ("**四周黑雾持续翻涌、飘移、流动，雾丝随气流变化**",
     "**贴地冷雾持续自左向右横流；魅影飘移中身形边缘不断剥离雾丝、向后拖曳拉长消散；一缕薄雾自镜头前虚焦飘过、穿出画面**"),

    # 5) 3.30–4.00s 雾句
    ("**四周黑雾仍持续翻涌飘动**",
     "**贴地冷雾仍自左向右横流、渐稀；魅影身形边缘残余雾丝继续向后拖曳、拉长、消散**"),

    # 6) OS 声音来源（去掉“四周黑雾”暗示，保持协调）
    ("声音从四周黑雾与虚空传来",
     "声音从虚空深处与暗场传来"),
]

# ---- 改 md（仅 14d-1 小节） ----
md = open(MD, encoding="utf-8").read()
s = md.index("## 镜头14d-1")
e = md.index("## 镜头14d-2")
sec = md[s:e]
for old, new in pairs:
    assert old in sec, f"MD 未命中: {old[:30]}"
    assert sec.count(old) == 1, f"MD 命中多次({sec.count(old)}): {old[:30]}"
    sec = sec.replace(old, new)
md2 = md[:s] + sec + md[e:]
open(MD, "w", encoding="utf-8").write(md2)
# 复核（仅针对 14d-1 小节 sec，避免 14d-2 同串误判）
for old, new in pairs:
    assert new in sec and old not in sec, f"sec 复核失败: {new[:20]}"
print("MD 14d-1 改写 OK；校验通过")

# ---- 改 DB vp(114) ----
con = sqlite3.connect(DB); cur = con.cursor()
cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=114")
vp = cur.fetchone()[0]
for old, new in pairs:
    assert old in vp, f"DB 未命中: {old[:30]}"
    assert vp.count(old) == 1, f"DB 命中多次({vp.count(old)}): {old[:30]}"
    vp = vp.replace(old, new)
cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=114", (vp,))
con.commit()
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()
print("DB vp(114) 同步 OK；校验通过")

# 终态计数
print("\n=== 终态核对 ===")
print("md 残留'四周黑雾':", md2.count("四周黑雾"))
print("md 含'彗尾':", md2.count("彗尾"), "| '自左向右':", md2.count("自左向右"), "| '虚焦飘过':", md2.count("虚焦飘过"))
print("md 含'派戏'说明:", "派戏" in md2)
