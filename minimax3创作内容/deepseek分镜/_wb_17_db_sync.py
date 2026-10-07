# -*- coding: utf-8 -*-
"""镜头17 DB 同步：分镜图 + 视频提示词，仅更新 shot 115（真正的镜头17 记录）。
truth source = 第1集_中文视频提示词_核对版.md（视频提示词）+ 第1集_分镜图提示词_GPT-Img2.md（分镜图）。
纪律：备份 -> 从 md 抽取 -> 更新 -> 断言 -> 回读。
"""
import sqlite3, shutil, os, re, json, datetime

DB = r'D:\Aicomfyui\短剧工作台\data\studio.db'
MD_VP = r'D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md'
MD_SB = r'D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_分镜图提示词_GPT-Img2.md'
SHOT_ID = 115
TS = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
BAK = DB + f'.bak-20260928-17sync-{TS}'

# ---------- 1. 备份 ----------
shutil.copy2(DB, BAK)
print('backup ->', BAK, os.path.getsize(BAK))

# ---------- 2. 从 md 抽取新内容 ----------
def sec_of(md_path, head):
    s = open(md_path, encoding='utf-8').read()
    i = s.find(head)
    m = re.search(r'\n## ', s[i+3:])
    return s[i:i+3+m.start()] if m else s[i:]

sec_vp = sec_of(MD_VP, '## 镜头17')
sec_sb = sec_of(MD_SB, '## 镜头17')

# 2a. video_prompt = 素材关系声明 ... 至 硬约束 之前
start = sec_vp.index('素材关系声明：')
end = sec_vp.index('硬约束：①')
video_prompt = sec_vp[start:end].strip()
# 归一成 CRLF（DB 约定）
video_prompt = video_prompt.replace('\r\n', '\n').replace('\n', '\r\n')

# 2b. hard_constraints = 硬约束 段 -> JSON 数组（6 条，去圈码前缀）
hc_text = sec_vp[sec_vp.index('硬约束：①')+len('硬约束：①'):]
# 切到下一个 ** 段（API参数）之前
nxt = re.search(r'\n\*\*', hc_text)
if nxt: hc_text = hc_text[:nxt.start()]
parts = re.split(r'[①②③④⑤⑥]', hc_text)
constraints = [p.strip().strip('*').strip('：').strip() for p in parts if p.strip()]
hard_constraints = json.dumps(constraints, ensure_ascii=False)

# 2c. image_prompt（分镜图提示词块，去掉 > 前缀，截到工作流注释前）
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

# 2d. image_refs_note = 上传参考图列表
ri = sec_sb.index('**上传参考图（按顺序）：**')
rj = sec_sb.index('**分镜图提示词：**')
refs_lines = sec_sb[ri:rj].split('\n')
image_refs_note = '\n'.join(l.strip() for l in refs_lines if l.strip()).replace('\r\n','\n').replace('\n','\r\n')

print('video_prompt len:', len(video_prompt))
print('hard_constraints count:', len(constraints))
print('image_prompt len:', len(image_prompt))
print('image_refs_note len:', len(image_refs_note))

# ---------- 3. 更新 DB ----------
db = sqlite3.connect(DB)
c = db.cursor()
c.execute('UPDATE shots SET title=? WHERE id=?', ('三魔化光波·过客双手格挡', SHOT_ID))
c.execute('''UPDATE shot_details SET
    video_prompt=?, hard_constraints=?, image_prompt=?, image_refs_note=?, image_target_name=?
    WHERE shot_id=?''',
    (video_prompt, hard_constraints, image_prompt, image_refs_note, '0117.jpg', SHOT_ID))
# first frame -> 0117.jpg
c.execute("UPDATE shot_frames SET file_name='0117.jpg', source='storyboard', note='镜头17 分镜图（17 新口径·待生成）' WHERE shot_id=? AND frame_type='first'", (SHOT_ID,))
# video side slot0 -> 0117.jpg
c.execute("UPDATE shot_asset_links SET file_name='0117.jpg', raw_text='0117.jpg（17 分镜图——首帧锚点 + 构图锚点）' WHERE shot_id=? AND target_side='video' AND slot_index=0", (SHOT_ID,))
# image side raw_text 对齐新参考描述
new_img_raw = [
    '0110_tail.jpg（镜头10 视频尾帧）— 内存黑洞王形态锚点：仅取形态（巨大石质岩体人形、头顶尖刺王冠、胸口漩涡巨口、体量远大于人）与暗紫色调；严禁带入其中的过客、红屏工位背景、面板文字与景别比例',
    '死循环妖_角色参考图.jpg（角色设定图）— 死循环妖形态锚点：仅取形态（黑发束髻、深色长袍、青色双环发光眼）与绿色能量／代码雨质感；严禁带入其拼贴排版与色值标注',
    '权限魅影_角色参考图 — 权限魅影形态锚点：仅取形态（完全实体的人形、清晰可辨的面孔、正常人的嘴部结构、一双紫色发光的瞳仁、身形修长、深色高领长袍）；严禁复制其拼贴排版与色值标注',
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

# ---------- 4. 断言 ----------
assert '三股光波' in video_prompt, 'vp 缺 三股光波'
assert '双手在身前抬起、掌心向前推出格挡' in video_prompt, 'vp 缺 双手格挡'
assert '三角形包围' not in video_prompt, 'vp 残留 三角形包围'
assert '双手交叉' not in video_prompt, 'vp 残留 双手交叉'
hc = json.loads(hard_constraints)
assert len(hc) == 6, f'hc 条数={len(hc)}'
assert any('正面左/中/右三向成形布局' in x for x in hc), 'hc 缺 正面三向布局'
assert any('双手在身前抬起、掌心向前推出格挡' in x for x in hc), 'hc 缺 双手格挡'
assert '三向光波' in image_prompt or '中/左/右三向光波' in image_prompt, 'image_prompt 缺 三向光波'
assert '三角形包围' not in image_prompt, 'image_prompt 残留 三角形包围'
print('ASSERTIONS PASSED')
print('backup:', BAK)
