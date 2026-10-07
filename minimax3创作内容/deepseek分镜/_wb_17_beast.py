# -*- coding: utf-8 -*-
"""镜头17 二改（2026-09-28 用户拍板）：
构图改同 0113b 的侧面机位；三道光全程幻化为龙/凤/虎三只能量光兽，三魔本体不出现。
落地：两份 md 镜头17 整节重写 + DB shot 115 同步。备份 -> 断言 -> 写盘 -> 回读。
"""
import sqlite3, shutil, os, re, json, datetime

DIR = r'D:\Aicomfyui\minimax3创作内容\deepseek分镜'
MD_VP = os.path.join(DIR, '第1集_中文视频提示词_核对版.md')
MD_SB = os.path.join(DIR, '第1集_分镜图提示词_GPT-Img2.md')
DB = r'D:\Aicomfyui\短剧工作台\data\studio.db'
SHOT_ID = 115
TS = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

# ================= 新小节文本 =================
NEW_SB = '''## 镜头17｜三道光兽（龙凤虎）·过客格挡（分镜图 0117.jpg）

**上传参考图（按顺序）：**
1. 0110_tail.jpg（镜头10 视频尾帧）— 内存黑洞王能量锚点：**仅取灰黑色调与巨型压逼体量感**；**严禁带入**其中的过客、红屏工位背景、面板文字、岩体人形本体与景别比例
2. 0112b_tail.jpg（镜头12b 视频尾帧）— 死循环妖能量锚点：**仅取绿色能量／代码雨质感**；**严禁带入**满屏 Error 弹窗碎片、绿色风暴包围构图、黑发束髻人形本体与正面特写景别
3. 权限魅影_角色参考图 — 权限魅影能量锚点：**仅取暗紫色调与紫光质感**；**严禁带入**其人形本体、拼贴排版与色值标注
4. 过客_角色参考图 — 严格锁定过客的面部特征、发型、服饰与体型

📋【工作流注释·非提示词·勿喂图像模型】：2026-09-28 用户二改推翻上一版"三魔本体悬于正面发波"构图（实拍出的图三魔压顶、与 0113b 衔接断裂）——本镜构图改为**同 0113b（死循环妖扑向工位镜头）的侧面机位**：过客在工位前、三道光从一侧冲来，且**三道光在冲近途中幻化为龙／凤／虎三只能量光兽**（绿龙=死循环妖、暗紫凤=权限魅影、灰黑虎=内存黑洞王），三魔本体不再出现在画面中，仅以光兽的色彩质感承袭各自锚点。

**分镜图提示词：**
> 参考图1（0110_tail.jpg）提供灰黑色调与巨型压逼体量参考——仅取色调与体量感，不取其中的人物、背景与景别比例。参考图2（0112b_tail.jpg）提供绿色能量／代码雨质感参考——仅取能量质感，不取其中人物与背景。参考图3（权限魅影_角色参考图）提供暗紫色调与紫光质感参考——仅取色调，严禁带入其人形本体、拼贴排版与色值标注。参考图4（过客_角色参考图）严格锁定过客的面部特征、发型、服饰与体型。竖屏9:16构图。侧面全景机位（同0113b机位方向）：过客站在工位前、位于画面左侧、侧身面向右侧来光方向；三股光流从画面右侧向他猛冲而来，冲近途中幻化为三只能量光兽——绿色光龙（死循环妖能量色）、暗紫光凤（权限魅影能量色）、灰黑光虎（内存黑洞王能量色、体量最大）——龙、凤、虎形态清晰可辨、拖曳光尾，呈品字形向过客压来。过客双手在身前抬起、掌心向前推出格挡，光兽前涌的光头撞在双手与周身被撑开激散成能量涟漪与飞溅光屑；过客被冲击力逼得微微后仰、踉跄后退半步，面部咬牙绷劲、眉微蹙、嘴唇微动似在说"三个……一起来？"，神情是强撑的倔强而非惊恐。背景：暗场办公室、显示器红光与报警红光交织、Error 弹窗碎片飞溅（呼应0113b氛围），过客身后的显示器红光形成逆光轮廓。画面中只有过客与三只光兽，三魔本体不出现（已完全化为光）；光兽的能量质感与过客写实人物形成风格对比。

> 📋 **【工作流注释 · 非提示词 · 勿喂图像模型】** 本图承接 14d-2 召唤完成后的态势——三魔已化作三股光、在冲近途中幻化为龙／凤／虎三只光兽冲向过客，过客侧身双手推出格挡；构图同 0113b（侧面机位、能量从一侧冲来），与核对版 17 段（三道光兽·过客格挡）严格对齐。
'''

NEW_VP = '''## 镜头17｜三道光兽（龙凤虎）·过客"三个……一起来？" · I2VA · 6秒

**API prompt（直接复制此段）：**

素材关系声明：
Audio 1：过客音色参考，台词"三个……一起来？"
Image 1（= Picture 1）：0117.jpg（17 分镜图，**待生成**）—— **视频首帧锚点 + 构图锚点**：侧面机位、过客在工位前侧身迎接三只能量光兽（绿龙／暗紫凤／灰黑虎）冲来、双手抬起推出格挡的瞬间（光兽色彩承袭三魔能量色；构图同 0113b）
Image 2：过客_角色参考图_GPT版.jpg —— 严格锁定过客的面部特征、发型、服饰与体型
Image 3：0110_tail.jpg（镜头10 视频尾帧）—— 灰黑色调与巨型体量感锚点（**仅取色调/质感/压逼体量**；严禁带入其中的过客、岩体人形本体与红屏工位环境）
Image 4：死循环妖_角色参考图.jpg（角色设定图）—— 绿色能量质感锚点（**锁死绿色能量／代码雨质感**；严禁带入其人形本体、拼贴排版与色值标注）
Image 5：权限魅影_角色参考图.jpg —— 暗紫光质感锚点（**仅取暗紫色调与紫光质感**；严禁带入其人形本体、拼贴排版与色值标注）

画面主体：侧面机位，过客站在工位前、面向来光方向；三股光流自画面一侧向他猛冲而来，冲近途中幻化为三只能量光兽——**绿色光龙（死循环妖）、暗紫光凤（权限魅影）、灰黑光虎（内存黑洞王、体量最大）**，龙、凤、虎形态清晰可辨、拖曳光尾。过客咬牙强撑，迎着冲近的光兽低声说**"三个……一起来？"**（**语气、语速、节奏一律照搬 Audio 1**）。三道光兽随即同时撞向过客；过客**双手在身前抬起、掌心向前推出格挡**，光兽撞在双手与周身被撑开激散，被冲击力逼得踉跄后退半步。画面中只有过客与三道光兽，三魔本体不出现（已完全化为光）。运镜：固定侧面中景、轻微推近（镜头本身不环绕），强化光兽压来的压逼感。

画面任务指令（严格按时序，画面与声音同步生成）：
0.0–1.0秒：侧面机位，三股光流自画面一侧向过客猛冲而来、拖曳光尾，冲近途中幻化出龙、凤、虎形态；过客重心下沉、双手抬起预备格挡。声音：三重能量低鸣合流（渐强）。
1.0–3.8秒：过客迎着冲近的光兽，**咬牙低声说（Audio 1）："三个……一起来？"**——**语气、语速、节奏一律照搬 Audio 1**，一气呵成、完整说完（实测净长约2.8秒，本窗口已按实测留足；不得加速压缩）。声音：台词为主；能量低鸣压至极低音量、不与台词抢声。
3.8–5.4秒：三道光兽**同时撞向过客**；过客**双手在身前抬起、掌心向前推出格挡**，光兽撞在双手与周身被撑开激散成能量涟漪与飞溅光屑，过客被冲击力推得踉跄后退半步。声音：三道光兽冲来撞击的能量爆鸣 + 蹬地后退的摩擦声 + 过客受冲击的一声闷哼（短促）。
5.4–6.0秒：定格——过客双手推出格挡、踉跄后退半步，三道光兽的光屑在他身前激散（构图同 Image 1）。声音：能量低鸣延续、渐收。

硬约束：① **画面中只有过客与三只能量光兽，三魔本体不得出现**（已完全化为光）；三道光兽形态清晰可辨且配色承袭各自能量锚点：绿色光龙（Image 4 能量色）、暗紫光凤（Image 5 能量色）、灰黑光虎（Image 3 色调、体量最大），光兽从来光方向冲向过客、拖曳光尾；② 过客**双手在身前抬起、掌心向前推出格挡**、动作有力，被逼得**踉跄后退半步**（不是被击飞、不是摔倒、不是撞翻）；③ 过客表情链：惊愕 → 咬牙绷劲（台词时）→ 受冲击紧绷，不惊恐尖叫、不面无表情；④ **台词必须一气呵成说完——不得中断、停顿、重复、改词，也不得拆成多个 utterance；台词的语气、语速、节奏、停顿一律以 Audio 1 为准，严禁按形容词自行演绎情绪**；⑤ 机位稳定：承接 Image 1 侧面机位状态，固定中景、轻微推近，**压迫感由光兽的冲势营造、镜头本身不环绕**，全程不切机位、不跳景别；⑥ **音效生成硬约束：三道光兽冲来撞击的能量爆鸣、蹬地后退的摩擦声、受冲击闷哼均由模型随画面同步生成，禁止静音成片；台词按 Audio 1 音色生成，所有音效音量低于台词、不与台词时段重叠抢声**。

**API参数：**
- ref_audio_0: 第1集_镜头17_过客_三个一起来.mp3（过客音色参考，台词窗口按实测校准）
- ref_image_0: 0117.jpg（17 分镜图，**待生成**——首帧锚点 + 构图锚点）
- ref_image_1: 过客_角色参考图_GPT版.jpg
- ref_image_2: 0110_tail.jpg（灰黑色调与巨型体量感锚点——仅取色调/质感/压逼体量；**严禁带入其中的过客、岩体人形本体与红屏工位环境**）
- ref_image_3: 死循环妖_角色参考图.jpg（绿色能量质感锚点——锁死绿色能量/代码雨质感；严禁带入其人形本体、拼贴排版与色值标注）
- ref_image_4: 权限魅影_角色参考图.jpg（暗紫光质感锚点——仅取暗紫色调与紫光质感；严禁带入其人形本体、拼贴排版与色值标注）
- duration: 6（台词实测净长约2.8秒 + 光兽冲来双手格挡后退半步；若实测台词≤1.5s 可缩回 5s）

**音频：**
- 角色：过客
- 音色：云希（Yunxi）| 语速默认 | 音调默认
- 台词："三个……一起来？"
- 语气：**完全由 ref_audio 文件本身决定**（上列语速/音调即全部可控项）——视频提示词不再重复描述语气
- ref_audio_0：第1集_镜头17_过客_三个一起来.mp3（**已生成**，实测约2.8秒——台词窗口按实测校准）

**后期音轨：（音效默认已由模型生成含在成片内，以下仅作兜底）**
- 台词默认由模型生成、已含在视频成片内，**后期无需另叠**；仅当生成结果台词缺失/念错时兜底替换：按实测时间窗（1.0-3.8s）叠 `第1集_镜头17_过客_三个一起来.mp3`
- 若模型未生成音效：3.8-5.4s 后期补三道光兽冲来撞击能量爆鸣+蹬地后退摩擦声（0-1.0s 三色能量低鸣由 16 尾帧氛围延续）

> 📋【工作流注释·勿喂模型】2026-09-28 用户二改构图：参照 0113b（死循环妖扑向工位镜头）改**侧面机位**，删"三魔本体成形→化光波"两段式，改为**三道光全程幻化为龙／凤／虎三只光兽冲来**（绿龙=死循环妖、暗紫凤=权限魅影、灰黑虎=内存黑洞王），三魔本体不出现；三张角色锚点 ref 降级为**色彩/能量质感锚点**。台词窗按实测2.8s重排（1.0–3.8s）。
'''

# ================= 1. 备份 =================
for p in (MD_VP, MD_SB, DB):
    b = p + f'.bak-{TS}-17beast'
    shutil.copy2(p, b)
    print('backup ->', b)

# ================= 2. md 整节替换 =================
def replace_section(md_path, head, new_text, tag):
    s = open(md_path, encoding='utf-8').read()
    i = s.find(head)
    assert i >= 0, f'{tag}: heading not found'
    m = re.search(r'\n## ', s[i+3:])
    end = i+3+m.start() if m else len(s)
    old = s[i:end]
    # 断言：旧内容里应有将被清除的旧口径词
    assert '三魔化光波' in old or '三向光波' in old, f'{tag}: old section unexpected'
    assert '三道光兽' not in old, f'{tag}: already rewritten?'
    s2 = s[:i] + new_text.rstrip('\n') + '\n' + s[end:]
    open(md_path, 'w', encoding='utf-8', newline='').write(s2)
    print(f'{tag}: replaced {len(old)} -> {len(new_text)} chars')

replace_section(MD_SB, '## 镜头17', NEW_SB, 'MD_SB')
replace_section(MD_VP, '## 镜头17', NEW_VP, 'MD_VP')

# ================= 3. DB 同步（沿用 _wb_17_db_sync.py 字段映射） =================
def sec_of(md_path, head):
    s = open(md_path, encoding='utf-8').read()
    i = s.find(head)
    m = re.search(r'\n## ', s[i+3:])
    return s[i:i+3+m.start()] if m else s[i:]

sec_vp = sec_of(MD_VP, '## 镜头17')
sec_sb = sec_of(MD_SB, '## 镜头17')

video_prompt = sec_vp[sec_vp.index('素材关系声明：'):sec_vp.index('硬约束：①')].strip()
video_prompt = video_prompt.replace('\r\n', '\n').replace('\n', '\r\n')

hc_text = sec_vp[sec_vp.index('硬约束：①')+len('硬约束：①'):]
nxt = re.search(r'\n\*\*', hc_text)
if nxt: hc_text = hc_text[:nxt.start()]
parts = re.split(r'[①②③④⑤⑥]', hc_text)
constraints = [p.strip().strip('*').strip('：').strip() for p in parts if p.strip()]
hard_constraints = json.dumps(constraints, ensure_ascii=False)

sb_i = sec_sb.index('**分镜图提示词：**')
lines = sec_sb[sb_i:].split('\n')
img_lines = []
for ln in lines[1:]:
    if ln.startswith('> 📋') or ln.startswith('>📋'):
        break
    if ln.startswith('> '):
        img_lines.append(ln[2:])
    elif ln.strip() == '' and img_lines:
        img_lines.append('')
    elif ln.startswith('**') or ln.startswith('## '):
        break
image_prompt = '\n'.join(img_lines).strip().replace('\r\n','\n').replace('\n','\r\n')

ri = sec_sb.index('**上传参考图（按顺序）：**')
rj = sec_sb.index('**分镜图提示词：**')
image_refs_note = '\n'.join(l.strip() for l in sec_sb[ri:rj].split('\n') if l.strip()).replace('\r\n','\n').replace('\n','\r\n')

db = sqlite3.connect(DB)
c = db.cursor()
c.execute('UPDATE shots SET title=? WHERE id=?', ('三道光兽（龙凤虎）·过客格挡', SHOT_ID))
c.execute('''UPDATE shot_details SET
    video_prompt=?, hard_constraints=?, image_prompt=?, image_refs_note=?, image_target_name=?
    WHERE shot_id=?''',
    (video_prompt, hard_constraints, image_prompt, image_refs_note, '0117.jpg', SHOT_ID))
c.execute("UPDATE shot_asset_links SET file_name='0117.jpg', raw_text='0117.jpg（17 分镜图——首帧锚点 + 构图锚点）' WHERE shot_id=? AND target_side='video' AND slot_index=0", (SHOT_ID,))
new_img_raw = [
    '0110_tail.jpg（镜头10 视频尾帧）— 内存黑洞王能量锚点：仅取灰黑色调与巨型压逼体量感；严禁带入其中的过客、红屏工位背景、面板文字、岩体人形本体与景别比例',
    '0112b_tail.jpg（镜头12b 视频尾帧）— 死循环妖能量锚点：仅取绿色能量／代码雨质感；严禁带入满屏 Error 弹窗碎片、绿色风暴包围构图、黑发束髻人形本体与正面特写景别',
    '权限魅影_角色参考图 — 权限魅影能量锚点：仅取暗紫色调与紫光质感；严禁带入其人形本体、拼贴排版与色值标注',
    '过客_角色参考图 — 严格锁定过客的面部特征、发型、服饰与体型',
]
c.execute("SELECT id FROM shot_asset_links WHERE shot_id=? AND target_side='image' ORDER BY slot_index", (SHOT_ID,))
img_ids = [r[0] for r in c.fetchall()]
assert len(img_ids) == 4, f'image side links={len(img_ids)}'
for lid, raw in zip(img_ids, new_img_raw):
    c.execute('UPDATE shot_asset_links SET raw_text=? WHERE id=?', (raw, lid))
db.commit()
db.close()
print('DB updated.')

# ================= 4. 断言（写盘后回读） =================
for p, tag in ((MD_VP,'MD_VP'), (MD_SB,'MD_SB')):
    s = open(p, encoding='utf-8').read()
    assert '三道光兽' in s, f'{tag}: 缺 三道光兽'
    assert '龙凤虎' in s or ('光龙' in s and '光凤' in s and '光虎' in s), f'{tag}: 缺 龙凤虎'
    assert '0113b' in s, f'{tag}: 缺 0113b 参照'
# vp 节内旧词清零
sec2 = sec_of(MD_VP, '## 镜头17')
assert '三魔本体不出现' in sec2
assert '三个魔头' not in sec2 and '三魔随即' not in sec2
assert '0.0–1.0秒' in sec2 and '1.0–3.8秒' in sec2 and '3.8–5.4秒' in sec2
assert '双手在身前抬起、掌心向前推出格挡' in sec2
# 14d-2 基准未波及
s_vp = open(MD_VP, encoding='utf-8').read()
d2 = s_vp[s_vp.find('## 镜头14d-2'):s_vp.find('## 镜头17')]
assert '0114d2_tail-无雾.jpg' in d2 and '三道光兽' not in d2, '14d-2 被波及！'
# DB 回读
db = sqlite3.connect(DB); c = db.cursor()
c.execute('select title from shots where id=?', (SHOT_ID,))
print('DB title:', c.fetchone()[0])
c.execute('select video_prompt from shot_details where shot_id=?', (SHOT_ID,))
db_vp = c.fetchone()[0].replace('\r\n','\n')
md_vp_body = sec_vp[sec_vp.index('素材关系声明：'):sec_vp.index('硬约束：①')].strip()
assert db_vp.strip() == md_vp_body.strip(), 'DB vp != md vp'
assert '三道光兽' in db_vp and '三魔本体不出现' in db_vp
c.execute('select hard_constraints from shot_details where shot_id=?', (SHOT_ID,))
hc = json.loads(c.fetchone()[0])
assert len(hc) == 6 and any('三魔本体不得出现' in x for x in hc)
c.execute('select image_prompt from shot_details where shot_id=?', (SHOT_ID,))
assert '光龙' in c.fetchone()[0]
db.close()
print('ALL ASSERTIONS PASSED')
print('TS =', TS)
