# -*- coding: utf-8 -*-
import os, re, subprocess, imageio_ffmpeg

EXE = imageio_ffmpeg.get_ffmpeg_exe()
ROOTS = [
    r'D:\Aicomfyui\minimax3创作内容\重制版\分镜视频',
]

def probe(p):
    r = subprocess.run([EXE, '-hide_banner', '-i', p],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    err = r.stderr
    v = re.search(r'Stream #\d+:\d+.*?: Video: (\w+).*', err)
    a = re.search(r'Stream #\d+:\d+.*?: Audio: (\w+).*', err)
    vline = v.group(0) if v else ''
    # 分辨率
    res = re.search(r', (\d{2,5})x(\d{2,5})', vline)
    w = int(res.group(1)) if res else 0
    h = int(res.group(2)) if res else 0
    # profile / pix_fmt
    prof = re.search(r'\(([\w ]+)\)', vline)
    pix = re.search(r'(yuv\w+p\w*|nv12|rgb\w*)', vline)
    fps = re.search(r'([\d.]+) fps', vline)
    prof_s = prof.group(1) if prof else ''
    bit = '10bit' if '10' in (pix.group(1) if pix else '') or '10' in prof_s else '8bit'
    return {
        'w': w, 'h': h,
        'codec': v.group(1) if v else '?',
        'profile': prof_s,
        'pix': pix.group(1) if pix else '?',
        'bit': bit,
        'fps': fps.group(1) if fps else '?',
        'audio': a.group(1) if a else '无',
        'mb': round(os.path.getsize(p) / 1048576, 2),
    }

rows = []
for root in ROOTS:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.lower().endswith('.mp4'):
                p = os.path.join(dp, f)
                try:
                    rows.append((f, probe(p)))
                except Exception as e:
                    rows.append((f, {'err': str(e)}))

print('%-26s %-11s %-9s %-8s %-16s %-6s %-6s %s' % ('文件', '分辨率', '编码', '色深', 'profile', 'fps', 'MB', '音轨'))
print('-' * 104)
for f, d in sorted(rows):
    if 'err' in d:
        print('%-26s ERR %s' % (f[:26], d['err'][:60])); continue
    print('%-26s %-11s %-9s %-8s %-16s %-6s %-6s %s' % (
        f[:26], '%dx%d' % (d['w'], d['h']), d['codec'], d['bit'],
        d['profile'][:16], d['fps'], d['mb'], d['audio']))

# 汇总
from collections import Counter
print()
print('分辨率分布:', dict(Counter('%dx%d' % (d['w'], d['h']) for f, d in rows if 'err' not in d)))
print('色深分布  :', dict(Counter(d['bit'] for f, d in rows if 'err' not in d)))
print('fps 分布  :', dict(Counter(d['fps'] for f, d in rows if 'err' not in d)))
