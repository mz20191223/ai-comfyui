# -*- coding: utf-8 -*-
"""验证 10-bit 原片 vs 8-bit 转码片是否有真实画质差异"""
import subprocess, os, numpy as np
from PIL import Image
import imageio_ffmpeg

EXE = imageio_ffmpeg.get_ffmpeg_exe()
D = r'D:\Aicomfyui\minimax3创作内容\重制版\分镜视频'
A = os.path.join(D, '0114a2.mp4')        # 10-bit
B = os.path.join(D, '0114a2_8bit.mp4')   # 8-bit 转码
TMP = r'D:\Aicomfyui\minimax3创作内容\白模预演\_cmp_tmp'
os.makedirs(TMP, exist_ok=True)

def grab(src, out, t):
    subprocess.run([EXE, '-hide_banner', '-loglevel', 'error', '-ss', str(t),
                    '-i', src, '-frames:v', '1', '-y', out], check=True)

def arr(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float64)

print('%-8s %-10s %-10s %-10s %s' % ('时间点', '平均差', '最大差', 'PSNR', '判定'))
print('-' * 56)
for t in ['0.50', '1.80', '3.20', '4.60']:
    pa = os.path.join(TMP, 'a_%s.png' % t)
    pb = os.path.join(TMP, 'b_%s.png' % t)
    grab(A, pa, t); grab(B, pb, t)
    a, b = arr(pa), arr(pb)
    n = min(a.shape[0], b.shape[0])
    a, b = a[:n], b[:n]
    d = np.abs(a - b)
    mse = (d ** 2).mean()
    psnr = 10 * np.log10(255 * 255 / mse) if mse > 0 else 99.0
    verdict = '肉眼无差异' if psnr > 40 else ('轻微差异' if psnr > 30 else '明显差异')
    print('%-8s %-10.3f %-10d %-10.1f %s' % (t + 's', d.mean(), int(d.max()), psnr, verdict))

print()
print('注：PSNR > 40dB 即超出人眼可辨范围；')
print('    若 10-bit 含真实高精度信息，降为 8-bit 会出现明显色阶损失（PSNR 显著偏低）。')
