# -*- coding: utf-8 -*-
import sqlite3, os, re, shutil, datetime

MD = r'D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md'
DB = r'D:\Aicomfyui\短剧工作台\data\studio.db'
AUDIO = r'D:\Aicomfyui\minimax3创作内容\重制版\音频\第1集_镜头17_过客_三个一起来.mp3'
ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

# 量时长（优先 mutagen，否则按文件大小估算）
dur = None
try:
    import mutagen
    dur = mutagen.File(AUDIO).info.length
except Exception:
    dur = os.path.getsize(AUDIO) * 8 / (128 * 1000)  # 128kbps 估算
dur_s = f'约{round(dur,1)}秒' if dur else '约2秒'
print('音频时长:', dur_s)

# ---------- 1. MD 真相源 ----------
raw = open(MD, 'rb').read()
if b'\r\n' in raw:
    raise SystemExit('md 含 CRLF，异常中止')
md = raw.decode('utf-8')
# 只改 音频 注释块里那处待生成（ref 块那处已是“按实测校准”，不动）
old_md = '- ref_audio_0：第1集_镜头17_过客_三个一起来.mp3（**待生成**，预计~2s——生成后按实测校准台词时间窗）'
new_md = f'- ref_audio_0：第1集_镜头17_过客_三个一起来.mp3（**已生成**，实测{dur_s}——台词窗口按实测校准）'
assert md.count(old_md) == 1, f'md old_md 命中数={md.count(old_md)}'
# 防呆：确认 ref 块那处没被误伤（应仍含“台词窗口按实测校准”且不含待生成之外的改动）
assert 'ref_audio_0: 第1集_镜头17_过客_三个一起来.mp3（过客音色参考，台词窗口按实测校准）' in md
md2 = md.replace(old_md, new_md)
assert '**待生成**' not in md2 or '过客_三个一起来' not in md2.split('**待生成**')[1][:50]
shutil.copy2(MD, MD + f'.bak-{ts}-17audio')
open(MD, 'w', encoding='utf-8').write(md2)
print('md 已更新, 备份', MD + f'.bak-{ts}-17audio')

# ---------- 2. DB shot 115 audio_note ----------
db = sqlite3.connect(DB)
c = db.cursor()
c.execute('select audio_note from shot_details where shot_id=115')
an = c.fetchone()[0]
old_db = '- ref_audio_0：第1集_镜头17_过客_三个一起来.mp3（待生成，预计~2s——生成后按实测校准台词时间窗）'
new_db = f'- ref_audio_0：第1集_镜头17_过客_三个一起来.mp3（过客音色参考，台词窗口按实测校准）\n- 时长：{dur_s}'
assert an.count(old_db) == 1, f'db old_db 命中数={an.count(old_db)}'
an2 = an.replace(old_db, new_db)
shutil.copy2(DB, DB + f'.bak-{ts}-17audio')
c.execute('update shot_details set audio_note=? where shot_id=115', (an2,))
db.commit()
db.close()
print('db audio_note 已更新, 备份', DB + f'.bak-{ts}-17audio')

# ---------- 3. 校验 ----------
md_v = open(MD, encoding='utf-8').read()
assert '**待生成**' not in md_v or '过客_三个一起来' not in md_v, 'md 仍含待生成'
db2 = sqlite3.connect(DB); cc = db2.cursor()
cc.execute('select audio_note from shot_details where shot_id=115')
an_v = cc.fetchone()[0]
db2.close()
assert '待生成' not in an_v, 'db 仍含待生成'
assert dur_s.split('约')[1].rstrip('秒') in an_v, 'db 时长未写入'
print('校验通过：md 与 db 的“待生成”均已清除，时长已写入')
