# -*- coding: utf-8 -*-
import sqlite3, shutil, os

MD = r"D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md"
DB = r"D:\Aicomfyui\短剧工作台\data\studio.db"

shutil.copy(MD, MD + ".bak-20260924-fog3")
for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        shutil.copy(DB + ext, DB + ext + ".bak-20260924-fog3")

pairs = [
    # 1) 说明行：加“生长曲线”
    ("⚠️ 雾气由模型生成并独立“派戏”：画面中的雾完全由模型自行生成、不依赖任何参考图、更不与魅影黏为一体。",
     "⚠️ 雾气由模型生成并独立“派戏”：画面中的雾完全由模型自行生成、不依赖任何参考图、更不与魅影黏为一体；**且雾在片内有一条“生长曲线”——0.00s 画面近乎无雾，随后由稀到浓逐渐弥漫生成，绝非开场就存在的静态浓雾层**。"),

    # 2) [Shot 1]：注明由稀到浓
    ("**环境雾由模型生成、与魅影分层独立运动**：",
     "**环境雾由模型生成、与魅影分层独立运动（由稀到浓逐渐生成，非开场即有的静态雾层）**："),

    # 3) 0.00–0.60s：近乎无雾 → 极薄冷雾刚漫开
    ("**贴画面下缘的灰白冷雾自左向右缓缓横流；魅影身形边缘开始剥离细小雾丝、向后拖曳消散，雾气有独立流动方向、不黏附角色、不是贴图**",
     "**画面近乎无雾；贴画面下缘刚刚生出极薄的灰白冷雾、自左向右缓缓漫开、雾量极稀；魅影身形边缘开始剥离细小雾丝、向后拖曳消散，雾气有独立流动方向、不黏附角色、不是贴图**"),

    # 4) 0.60–3.30s：由薄转浓
    ("**贴地冷雾持续自左向右横流；魅影飘移中身形边缘不断剥离雾丝、向后拖曳拉长消散；一缕薄雾自镜头前虚焦飘过、穿出画面**",
     "**贴地冷雾由薄转浓、逐渐弥漫增厚，持续自左向右横流；魅影飘移中身形边缘不断剥离雾丝、向后拖曳拉长消散；一缕薄雾自镜头前虚焦飘过、穿出画面**"),
]

# ---- md（仅 14d-1 小节） ----
md = open(MD, encoding="utf-8").read()
s = md.index("## 镜头14d-1"); e = md.index("## 镜头14d-2")
sec = md[s:e]
for old, new in pairs:
    assert old in sec, f"MD 未命中: {old[:32]}"
    assert sec.count(old) == 1, f"MD 命中多次({sec.count(old)}): {old[:32]}"
    sec = sec.replace(old, new)
assert "生长曲线" in sec and "画面近乎无雾" in sec
md2 = md[:s] + sec + md[e:]
open(MD, "w", encoding="utf-8").write(md2)
print("MD 14d-1 生长曲线 OK")

# ---- DB vp(114) ----
con = sqlite3.connect(DB); cur = con.cursor()
cur.execute("SELECT video_prompt FROM shot_details WHERE shot_id=114")
vp = cur.fetchone()[0]
for old, new in pairs:
    assert old in vp, f"DB 未命中: {old[:32]}"
    assert vp.count(old) == 1, f"DB 命中多次({vp.count(old)}): {old[:32]}"
    vp = vp.replace(old, new)
assert "生长曲线" in vp and "画面近乎无雾" in vp
cur.execute("UPDATE shot_details SET video_prompt=? WHERE shot_id=114", (vp,))
con.commit()
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.close()
print("DB vp(114) 生长曲线 OK; len =", len(vp))

print("\n=== 14d-1 终态 ===")
print("生长曲线:", "生长曲线" in sec, "| 近乎无雾:", "画面近乎无雾" in sec,
      "| 由薄转浓:", "由薄转浓" in sec, "| 派戏:", "派戏" in sec,
      "| 四周黑雾:", sec.count("四周黑雾"), "| 无雾首帧:", "0114d不带雾.jpg" in sec)
