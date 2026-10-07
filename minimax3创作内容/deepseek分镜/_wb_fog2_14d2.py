# -*- coding: utf-8 -*-
import sqlite3, shutil, os

MD = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"
DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"

shutil.copy(MD, MD + ".bak-20260924-fog2b")
for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        shutil.copy(DB + ext, DB + ext + ".bak-20260924-fog2b")

# 8 处替换（14d-2：魅影向后飘移撤离 + 召唤两妖）
pairs = [
    # 1) 说明行
    ("⚠️ 雾气由模型生成：画面中的雾完全由模型自行生成，不依赖任何参考图；雾是独立的环境大气层次，始终灵动飘散、不随人物刚性位移、不被当贴图冻结。",
     "⚠️ 雾气由模型生成并独立“派戏”：画面中的雾完全由模型自行生成、不依赖任何参考图、更不与魅影黏为一体。雾分三层——①贴画面下缘的灰白冷雾自左向右缓缓横流，两妖浮现处被召唤气流扰动、缓缓荡开；②魅影自身向后飘移时，半透明身形边缘不断剥离出细小雾丝、向前拖曳、拉长、消散（彗尾效应）；③偶有一缕薄雾自镜头前虚焦飘过、穿出画面。魅影核心比环境雾更实、略亮；环境雾更暗更稀，二者明确分层。"),

    # 2) [Shot 1] 整段雾句
    ("**四周黑雾（由模型生成）持续翻涌、飘移、动态流动，雾丝随气流不断变形，与魅影飘移形成纵深层次，雾气有独立生命、绝非静止贴图**",
     "**环境雾由模型生成、与魅影分层独立运动**：贴画面下缘的灰白冷雾自左向右缓缓横流；魅影自身向后飘移时，半透明身形边缘不断剥离出细小雾丝、向前拖曳、拉长、消散，形成流动的彗尾；偶有一缕薄雾自镜头前虚焦飘过、穿出画面，制造纵深；魅影核心比环境雾更实、略亮，环境雾更暗更稀，二者不黏连**"),

    # 3) OS 声音来源
    ("声音从四周黑雾与虚空传来",
     "声音从虚空深处与暗场传来"),

    # 4) 0.00–0.50s 雾句
    ("**四周黑雾持续翻涌飘动**",
     "**贴地冷雾自左向右缓缓横流；魅影向后飘移，身形边缘开始剥离雾丝、向前拖曳消散，雾气有独立流动方向、不黏附角色**"),

    # 5) 0.50–1.30s 雾句
    ("**四周黑雾持续翻涌、飘移**",
     "**贴地冷雾持续自左向右横流；一缕薄雾自镜头前虚焦飘过、穿出画面**"),

    # 6) 1.30–4.00s 雾句
    ("**四周黑雾持续翻涌、飘移、流动，雾丝随气流变形**",
     "**贴地冷雾持续自左向右横流；魅影向后飘移中身形边缘不断剥离雾丝、向前拖曳拉长消散；一缕薄雾自镜头前虚焦飘过、穿出画面**"),

    # 7) 左妖浮现段补雾扰动
    ("魅影已飘移至中远景位、左侧空间展开。",
     "魅影已飘移至中远景位、左侧空间展开；**左侧虚空处的贴地冷雾被召唤气流扰动、自左前方缓缓荡开**。"),

    # 8) 右妖浮现段补雾扰动 + 06.1–7.0s 收束段雾句
    ("下半身留在画外（巨型体量靠出画表达，不缩体完整入画）；(S1) 保持静默；镜头保持静止、三者同框。",
     "下半身留在画外（巨型体量靠出画表达，不缩体完整入画）；(S1) 保持静默；镜头保持静止、三者同框；**右侧虚空的贴地冷雾随之被气流推开、缓缓荡开**。"),

    # 9) 06.10–07.00s 收束段雾句
    ("**四周黑雾仍持续翻涌、飘移、流动**",
     "**贴地冷雾仍自左向右横流、渐稀；魅影身形边缘残余雾丝继续向前拖曳、拉长、消散**"),
]

# ---- 改 md（仅 14d-2 小节） ----
md = open(MD, encoding="utf-8").read()
s2 = md.index("## 镜头14d-2")
e2 = md.index("\n## 镜头17｜", s2)
sec = md[s2:e2]
for old, new in pairs:
    assert old in sec, f"MD 未命中: {old[:34]}"
    assert sec.count(old) == 1, f"MD 命中多次({sec.count(old)}): {old[:34]}"
    sec = sec.replace(old, new)
assert sec.count("四周黑雾") == 0, f"14d-2 仍残留'四周黑雾' x{sec.count('四周黑雾')}"
md2 = md[:s2] + sec + md[e2:]
open(MD, "w", encoding="utf-8").write(md2)
print("MD 14d-2 改写 OK；14d-2 内'四周黑雾'残留 =", sec.count("四周黑雾"))

# ---- 改 DB vp(182) ----
con = sqlite3.connect(DB); cur = con.cursor()
cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=182")
vp = cur.fetchone()[0]
for old, new in pairs:
    assert old in vp, f"DB 未命中: {old[:34]}"
    assert vp.count(old) == 1, f"DB 命中多次({vp.count(old)}): {old[:34]}"
    vp = vp.replace(old, new)
assert vp.count("四周黑雾") == 0, f"DB vp 仍残留'四周黑雾' x{vp.count('四周黑雾')}"
cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=182", (vp,))
con.commit()
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()
print("DB vp(182) 同步 OK；'四周黑雾'残留 =", vp.count("四周黑雾"))

# ---- 终态核对 ----
print("\n=== 终态核对 ===")
print("md 14d-1 段 彗尾 x", md2[md2.index('## 镜头14d-1'):md2.index('## 镜头14d-2')].count("彗尾"))
print("md 14d-2 段 彗尾 x", sec.count("彗尾"), "| 自左向右 x", sec.count("自左向右"))
print("md 全文 '派戏' 说明行数 =", md2.count("派戏"))
print("md 全文 残留'四周黑雾'（应仅剩其他镜头）=", md2.count("四周黑雾"))
