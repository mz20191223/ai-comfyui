# -*- coding: utf-8 -*-
# 14d-2 落地：首帧换 0114d2_tail-无雾.jpg + 补魅影角色锚点(Picture 2/ref_image_1) + 雾生长曲线 + 衔接14d-1
# 范围：md 的「## 镜头14d-2」节 + DB shot 182（video_prompt / video侧links / first帧 / files索引）
import os, sys, time, shutil, sqlite3, hashlib

MD = r'D:/Aicomfyui/minimax3创作内容/deepseek分镜/第1集_中文视频提示词_核对版.md'
DB = r'D:/Aicomfyui/短剧工作台/data/studio.db'
NEWIMG_NAME = '0114d2_tail-无雾.jpg'
NEWIMG_PATH = r'D:/Aicomfyui/minimax3创作内容/重制版/分镜图/视频尾帧/0114d2_tail-无雾.jpg'
TS = time.strftime('%Y%m%d_%H%M%S')

# ---------- 替换对（R1-R9 同时作用于 md 节与 DB vp；R10 仅 md 节） ----------
R = []

R.append((
"Picture 1：0114d不带雾.jpg — 首帧锚点（0.00s）+ 人物/结构参考（无雾）：承接 14b-2 尾帧的无雾版本，魅影为半透明灰白雾态人形、形态完整、双臂垂放的远景，镜头保持静止、魅影自身向后缓缓飘移远离，背景为虚化暗场、工位剪影隐去、左右虚空全空、画面中无人物无妖",
"Picture 1：0114d2_tail-无雾.jpg — 首帧锚点（0.00s）+ 人物/结构参考（无雾）：承接 14d-1 尾帧的去雾版本，权限魅影为半透明暗色雾质人形、形态完整、面部隐于暗色雾中只露一双紫色发光瞳仁、无嘴、全身悬浮于画面中央、双臂垂放、姿态与 14d-1 结尾完全一致，背景为虚化熄灯办公区、工位剪影隐约可见、画面中无他人无妖"))

R.append((
"更不与魅影黏为一体。雾分三层——①贴画面下缘的灰白冷雾自左向右缓缓横流，两妖浮现处被召唤气流扰动、缓缓荡开",
"更不与魅影黏为一体；**且雾在片内有一条“生长曲线”——0.00s 画面近乎无雾，随后由稀到浓逐渐弥漫生成，绝非开场就存在的静态浓雾层**。雾分三层——①贴画面下缘的灰白冷雾自左向右缓缓横流，两妖浮现处被召唤气流扰动、缓缓荡开"))

R.append((
"""Picture 2：死循环妖_角色参考图.jpg — 死循环妖形态：黑发束髻、深色长袍、青色双环发光眼、绿色能量质感
Picture 3：0110_tail.jpg — 内存黑洞王形态：仅取巨大体型与暗色质感（严禁带入其中的过客与红色警示屏）
Picture 4：公司办公室_场景参考图.jpg — 仅作熄灯办公区的暗调氛围参考""",
"""Picture 2：权限魅影_角色参考图.jpg — 角色身份锚点（**形态参考·非首帧**）：全片魅影的形态与质感严格以图中「MAIN FORM」的权限魅影为唯一依据——暗色雾质人形、半透明、整个身体由烟雾构成、面部隐于暗色雾中只露一双紫色发光瞳仁、无嘴、体态修长（非健美肌肉体型）；本图**只提供「角色本体长什么样」**（形态/质感/瞳色）；画面内容、构图、光线与运镜一律以 Picture 1 与下方时序为准；图内的分格排版、色卡、蓝色图标与标题文字均属设定板版式、与角色本体无关
⚠️ 角色一致性（Picture 1 与 Picture 2 为同一人）：魅影在本片自始至终是 Picture 2 那位——同一副暗色雾质人形躯体、同一双紫色发光瞳仁、同样无嘴、同样修长体态、通体由雾构成且边缘持续消散；从首帧到片尾是同一个角色，形态与质感保持稳定
Picture 3：死循环妖_角色参考图.jpg — 死循环妖形态：黑发束髻、深色长袍、青色双环发光眼、绿色能量质感
Picture 4：0110_tail.jpg — 内存黑洞王形态：仅取巨大体型与暗色质感（严禁带入其中的过客与红色警示屏）
Picture 5：公司办公室_场景参考图.jpg — 仅作熄灯办公区的暗调氛围参考"""))

R.append((
"[Shot 1] 竖屏 9:16，单一连续镜头（无转场、无黑场、无字幕）。以 Picture 1（0114d不带雾.jpg·承接 14b-2 尾帧的无雾版）为起点、镜头保持静止不动、魅影自身向后缓缓飘移远离镜头：权限魅影（S1，雾态人形）于远景中双臂垂放、身形较小，魅影自中近景位自身向后缓缓飘移远离、稳居画面中央偏后，逐步带出左右两侧空旷的暗场，为两妖浮现留出空间；**环境雾由模型生成、与魅影分层独立运动**：",
"[Shot 1] 竖屏 9:16，单一连续镜头（无转场、无黑场、无字幕）。以 Picture 1（0114d2_tail-无雾.jpg·承接 14d-1 尾帧的去雾版）为起点、镜头保持静止不动、魅影自身向后缓缓飘移远离镜头：权限魅影（S1，雾态人形）全身悬浮于画面中央、双臂垂放、姿态与 14d-1 结尾完全一致，**形态与质感严格对齐 Picture 2 的权限魅影（同一副暗色雾质人形躯体、同一双紫色发光瞳仁、无嘴、修长体态）**，魅影自全身景位自身向后缓缓飘移远离、稳居画面中央偏后，逐步带出左右两侧空旷的暗场，为两妖浮现留出空间；**环境雾由模型生成、与魅影分层独立运动（由稀到浓逐渐生成，非开场即有的静态雾层）**："))

R.append((
"二者不黏连**；工位剪影完全隐去不出现于画面。",
"二者不黏连**；背景为虚化的熄灯办公区、工位剪影隐约可见（与首帧一致）、不抢主体，画面中无任何人类角色。"))

R.append((
"00:00.000–00:00.500：**画外音(OS)念出 [中文]出来吧~**——声音从虚空深处与暗场传来，低沉、干脆、略带命令感（仅四字、约 0.5 秒、不拖长）；(S1) 本人不开口、不做任何口型动作；魅影自身向后缓缓飘移远离镜头（镜头保持静止）；**贴地冷雾自左向右缓缓横流；魅影向后飘移，身形边缘开始剥离雾丝、向前拖曳消散，雾气有独立流动方向、不黏附角色**。",
"00:00.000–00:00.500：(S1) 保持 Picture 1 的姿态，全身悬浮、双臂垂放、缓缓浮动；**画外音(OS)念出 [中文]出来吧~**——声音从虚空深处与暗场传来，低沉、干脆、略带命令感（仅四字、约 0.5 秒、不拖长）；(S1) 本人不开口、不做任何口型动作；魅影自身向后缓缓飘移远离镜头（镜头保持静止）；**画面近乎无雾；贴画面下缘刚刚生出极薄的灰白冷雾、自左向右缓缓漫开、雾量极稀；魅影向后飘移，身形边缘开始剥离雾丝、向前拖曳消散，雾气有独立流动方向、不黏附角色、不是贴图**。"))

R.append((
"左侧虚空中死循环妖（Picture 2）由虚化缓缓凝实浮现",
"左侧虚空中死循环妖（Picture 3）由虚化缓缓凝实浮现"))

R.append((
"右侧虚空中内存黑洞王（Picture 3，体型远大于魅影）继之凝实浮现",
"右侧虚空中内存黑洞王（Picture 4，体型远大于魅影）继之凝实浮现"))

R.append((
"""- ref_image_0: 0114d不带雾.jpg（**首帧锚点·人物结构参考·无雾**：承接 14b-2 尾帧的无雾版本，魅影半透明灰白雾态、形态完整、双臂垂放的远景、镜头保持静止、魅影自身向后缓缓飘移远离、背景虚化暗场、工位剪影隐去、左右虚空全空、无过客无妖）
- ref_image_1: 死循环妖_角色参考图.jpg（角色设定图——死循环妖形态锚点：**黑发束髻、深色长袍、青色双环发光眼**＋绿色能量质感；严禁拼贴排版与色值标注）
- ref_image_2: 0110_tail.jpg（镜头10 视频尾帧——内存黑洞王形态锚点，**仅取形态/质感/色调/巨大体型**；**严禁带入其中的过客与红屏工位环境**）
- ref_image_3: 公司办公室_场景参考图.jpg""",
"""- ref_image_0: 0114d2_tail-无雾.jpg（**首帧锚点·人物结构参考·无雾**：承接 14d-1 尾帧的去雾版本，魅影半透明暗色雾质人形、形态完整、面部隐于暗雾只露一双紫色发光瞳仁、无嘴、全身悬浮居中、双臂垂放、姿态与 14d-1 结尾一致、镜头保持静止、魅影自身向后缓缓飘移远离、背景虚化熄灯办公区、工位剪影隐约可见、左右虚空渐次展开、无过客无妖）
- ref_image_1: 权限魅影_角色参考图.jpg（**角色身份锚点·形态参考**：全片魅影的形态/质感/瞳色以此为唯一依据——暗色雾质人形、半透明、身体由雾构成、面部隐于暗雾只露一双紫色发光瞳仁、无嘴、体态修长；只取角色本体（形态/质感/瞳色），设定板的分格、色卡、图标、标题文字与图中缠绕的具象雾丝都不属于角色本体）
- ref_image_2: 死循环妖_角色参考图.jpg（角色设定图——死循环妖形态锚点：**黑发束髻、深色长袍、青色双环发光眼**＋绿色能量质感；严禁拼贴排版与色值标注）
- ref_image_3: 0110_tail.jpg（镜头10 视频尾帧——内存黑洞王形态锚点，**仅取形态/质感/色调/巨大体型**；**严禁带入其中的过客与红屏工位环境**）
- ref_image_4: 公司办公室_场景参考图.jpg"""))

R_MD_ONLY = [(
"> ⚠️ 风险同 14d-1：镜头内无有脸角色，OS 仍可能乱语；若翻车走后期叠轨。",
"> ⚠️ 风险同 14d-1：镜头内无有脸角色，OS 仍可能乱语；若翻车走后期叠轨。\n> **2026-09-25 首帧换图（跨镜衔接·用户决策）**：首帧改用 `0114d2_tail-无雾.jpg`＝14d-1 尾帧（0114d1_tail.jpg）的 I2I 去雾版（用户 09-25 出图，命名与早前建议不同、以实际文件为准）——14d-2 以 14d-1 结尾姿态（全身悬浮、双臂垂放）开场、动作自然衔接；尾帧原有的模型生成雾已在去雾图中抹除，雾仍全由模型自生成（派戏＋生长曲线）。同轮补挂视频侧魅影角色锚点（Picture 2 / ref_image_1，同 14d-1 范式）。"),
(
"**首帧改用 0114d不带雾.jpg**（2026-09-24 双参考证伪：带雾参考图被 H3 当凝固贴图附着角色；改为仅无雾首帧，雾全由模型自生成）",
"**首帧改用 0114d2_tail-无雾.jpg**（2026-09-25 跨镜衔接·承接 14d-1 尾帧去雾版；此前 09-24 曾用 0114d不带雾.jpg——双参考证伪：带雾参考图被 H3 当凝固贴图附着角色，改用无雾首帧，雾全由模型自生成）")]

def apply(txt, pairs):
    for old, new in pairs:
        n = txt.count(old)
        assert n == 1, f'锚点命中 {n} 次(应为1): {old[:40]}...'
        txt = txt.replace(old, new)
    return txt

# ---------- 前置断言 ----------
assert os.path.exists(NEWIMG_PATH), '去雾尾帧不存在: ' + NEWIMG_PATH
raw = open(MD, 'rb').read()
assert raw.count(b'\r\n') == 0, 'md 出现 CRLF，异常'
s = raw.decode('utf-8')
hs = s.find('## 镜头14d-2')
assert hs > 0
m = None
import re
m = re.search(r'\n## ', s[hs+3:])
he = hs + 3 + m.start() if m else len(s)
sec = s[hs:he]
for probes in ['0114d不带雾.jpg', 'Picture 2：死循环妖', 'ref_image_0: 0114d不带雾.jpg']:
    assert probes in sec, '节内缺探针: ' + probes

# md 节替换（R1-R9 + R10）
new_sec = apply(sec, R + R_MD_ONLY)
s_new = s[:hs] + new_sec + s[he:]

# 提取新 vp 块（与 DB vp 同源）：从 **API prompt 到节尾（--- 前）
k = new_sec.find('**API prompt')
assert k > 0
tail = new_sec[k:]
cut = tail.rfind('\n---')
vp_md = (tail[:cut] if cut > 0 else tail).strip()
vp_lf = vp_md.replace('\r\n', '\n')
for must in ['0114d2_tail-无雾.jpg', 'Picture 2：权限魅影_角色参考图.jpg',
             '（Picture 3）由虚化缓缓凝实浮现', '（Picture 4，体型远大于魅影）',
             'ref_image_4: 公司办公室_场景参考图.jpg', '生长曲线']:
    assert must in vp_lf, '新vp缺要素: ' + must
for ban in ['0114d不带雾.jpg', '14b-2 尾帧', 'ref_image_3: 公司办公室']:
    assert ban not in vp_lf, '新vp残留旧文: ' + ban

# ---------- 备份 ----------
bak_md = MD.replace('.md', f'_14d2_bak_{TS}.md')
shutil.copy2(MD, bak_md)
for ext in ['', '-wal', '-shm']:
    p = DB + ext
    if os.path.exists(p):
        shutil.copy2(p, p + f'.bak_14d2_{TS}')
print('备份完成:', bak_md)

# ---------- 写 md（全部断言通过后才落盘） ----------
open(MD, 'wb').write(s_new.encode('utf-8'))
# 立即回读校验
rb = open(MD, 'rb').read().decode('utf-8')
hs2 = rb.find('## 镜头14d-2')
m2 = re.search(r'\n## ', rb[hs2+3:])
he2 = hs2 + 3 + m2.start() if m2 else len(rb)
sec2 = rb[hs2:he2]
assert '0114d2_tail-无雾.jpg' in sec2 and 'Picture 5：公司办公室' in sec2
# 残留检查只对 vp 块（工作流注释允许留历史记录）
vp_sec2 = sec2[sec2.find('**API prompt'):]
assert '0114d不带雾.jpg' not in vp_sec2
# 14d-1 节必须一字未动
i1 = rb.find('## 镜头14d-1'); j1 = rb.find('## 镜头14d-2')
assert 'ref_image_0: 0114d不带雾.jpg' in rb[i1:j1] and 'Picture 2：权限魅影_角色参考图.jpg' in rb[i1:j1]
assert rb.count('镜头14d-1') == s.count('镜头14d-1') and rb.count('## ') == s.count('## ')
print('md 写入+回读校验 OK')

# ---------- DB ----------
con = sqlite3.connect(DB, timeout=15)
c = con.cursor()
c.execute("select id,slot_index,file_name from shot_asset_links where shot_id=182 and target_side='video' order by slot_index")
links = c.fetchall()
assert links == [(2739, 0, '0114d不带雾.jpg'), (2741, 1, '死循环妖_角色参考图.jpg'),
                 (2742, 2, '0110_tail.jpg'), (2743, 3, '公司办公室_场景参考图.jpg')], f'links 现状不符: {links}'
c.execute("select id,file_name from shot_frames where shot_id=182 and frame_type='first'")
fr = c.fetchall()
assert fr == [(153, '0114d不带雾.jpg')], f'first帧现状不符: {fr}'
c.execute("select count(*) from files where file_name=?", (NEWIMG_NAME,))
assert c.fetchone()[0] == 0, 'files 已有该图，异常'

# files 索引
size = os.path.getsize(NEWIMG_PATH)
sha1 = hashlib.sha1(open(NEWIMG_PATH, 'rb').read()).hexdigest()
wh = (None, None)
try:
    from PIL import Image
    im = Image.open(NEWIMG_PATH); wh = im.size
except Exception:
    pass
now = time.strftime('%Y-%m-%d %H:%M:%S')
c.execute("insert into files(path,file_name,ext,file_type,size_bytes,width,height,duration_sec,sha1,exists_flag,indexed_at,last_seen_at) values(?,?,?,?,?,?,?,?,?,1,?,?)",
          (r'D:\Aicomfyui\minimax3创作内容\重制版\分镜图\视频尾帧\0114d2_tail-无雾.jpg', NEWIMG_NAME, '.jpg', 'image', size, wh[0], wh[1], None, sha1, now, now))

# video 侧 links：slot0 换图；slot 3→4→...；插入 slot1 魅影锚点
note0 = ('0114d2_tail-无雾.jpg（承接 14d-1 尾帧去雾版：魅影半透明暗色雾质人形、形态完整、面部隐于暗雾只露一双紫色发光瞳仁、'
         '无嘴、全身悬浮居中、双臂垂放、姿态与 14d-1 结尾一致、镜头保持静止、魅影自身向后缓缓飘移远离、'
         '背景虚化熄灯办公区、工位剪影隐约可见、无过客无妖）')
c.execute("update shot_asset_links set file_name=?, take_note=?, raw_text=? where id=2739", (NEWIMG_NAME, note0, note0))
c.execute("update shot_asset_links set slot_index=4 where id=2743")
c.execute("update shot_asset_links set slot_index=3 where id=2742")
c.execute("update shot_asset_links set slot_index=2 where id=2741")
note1 = '只取角色本体（暗色雾质人形/半透明/修长体态/一双紫色发光瞳仁/无嘴）；不取拼贴分格、色卡、蓝色图标、标题文字；不取图中缠绕的具象雾丝（雾由模型生成）'
c.execute("insert into shot_asset_links(shot_id,asset_id,asset_image_id,role,slot_index,target_side,ref_version,take_note,file_name,raw_text,created_at) values(182,NULL,NULL,'形态锚点',1,'video','concept',?,?,NULL,?)",
          (note1, '权限魅影_角色参考图.jpg', now))

# first 帧换图
c.execute("select file_path from shot_frames where id=153")
fp = c.fetchone()[0]
c.execute("update shot_frames set file_name=?, file_path=? where id=153",
          (NEWIMG_NAME, r'D:\Aicomfyui\minimax3创作内容\重制版\分镜图\视频尾帧\0114d2_tail-无雾.jpg' if fp else fp))

# video_prompt（CRLF）
vp_crlf = vp_lf.replace('\n', '\r\n')
c.execute("update shot_details set video_prompt=?, updated_at=? where shot_id=182", (vp_crlf, now))
con.commit()

# ---------- DB 回读校验 ----------
c.execute("select slot_index,file_name from shot_asset_links where shot_id=182 and target_side='video' order by slot_index")
got = c.fetchall()
assert got == [(0, '0114d2_tail-无雾.jpg'), (1, '权限魅影_角色参考图.jpg'), (2, '死循环妖_角色参考图.jpg'),
               (3, '0110_tail.jpg'), (4, '公司办公室_场景参考图.jpg')], f'回读links不符: {got}'
c.execute("select video_prompt from shot_details where shot_id=182")
vp_db = c.fetchone()[0].replace('\r\n', '\n').strip()
assert vp_db == vp_lf, 'DB vp 与 md vp 不一致！'
c.execute("select file_name from shot_frames where id=153")
assert c.fetchone()[0] == NEWIMG_NAME
c.execute("select count(*) from files where file_name=? and exists_flag=1", (NEWIMG_NAME,))
assert c.fetchone()[0] == 1
con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
con.close()
print('DB 写入+回读校验 OK（links 5 槽 / first帧 / vp 与 md 逐字一致 / files 已索引）')
print('ALL DONE 14d-2 落地完成')
