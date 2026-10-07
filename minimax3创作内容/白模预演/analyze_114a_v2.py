# -*- coding: utf-8 -*-
"""0114a.mp4 抽帧 + 音频波形分析"""
import os, subprocess, csv
import numpy as np
import cv2
from PIL import Image, ImageDraw

SRC = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\0114a.mp4"
OUT = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\_0114a分析"
os.makedirs(OUT, exist_ok=True)

FFMPEG = r"C:\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"

# ---------- 1. 视频基本信息 ----------
cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
dur_v = nframes / fps if fps else 0
print(f"视频: {W}x{H} fps={fps:.2f} 帧数={nframes} 时长={dur_v:.2f}s")

# ---------- 2. 抽帧 ----------
frames = []
idx = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
    idx += 1
cap.release()
print(f"读入 {len(frames)} 帧")

# 逐帧亮度 + 帧间差
prev = None
rows = []
for i, f in enumerate(frames):
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
    bright = g.mean()
    detail = cv2.Laplacian(g, cv2.CV_32F).std()
    if prev is None:
        diff = 0.0
    else:
        diff = np.abs(g - prev).mean()
    prev = g
    rows.append((i / fps, bright, detail, diff))

print("\n=== 逐 0.25s 画面指标（亮/细节/帧间差）===")
print(f"{'t(s)':>6} {'亮度':>7} {'细节':>7} {'帧间差':>7}")
step = max(1, int(fps * 0.25))
for i in range(0, len(rows), step):
    t, b, d, df = rows[i]
    print(f"{t:6.2f} {b:7.2f} {d:7.2f} {df:7.2f}")

# 全黑帧检测
black = [(t, b) for t, b, d, df in rows if b < 3.0]
if black:
    print(f"\n!! 检测到 {len(black)} 个近全黑帧，时段 {black[0][0]:.2f}s ~ {black[-1][0]:.2f}s")

# 大跳变检测（疑似转场）
big = [(t, df) for t, b, d, df in rows if df > 8.0]
if big:
    print(f"!! 检测到 {len(big)} 个帧间大跳变(>8)，时间点: " +
          ", ".join(f"{t:.2f}s" for t, _ in big[:20]))

# ---------- 3. 拼图 ----------
n_pick = 20
picks = np.linspace(0, len(frames) - 1, n_pick).astype(int)
cols, rows_n = 5, 4
tw, th = W // 4, H // 4
sheet = Image.new("RGB", (cols * tw, rows_n * (th + 22)), (20, 20, 20))
dr = ImageDraw.Draw(sheet)
for k, pi in enumerate(picks):
    f = frames[pi]
    img = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).resize((tw, th))
    r, c = divmod(k, cols)
    x, y = c * tw, r * (th + 22)
    sheet.paste(img, (x, y))
    dr.text((x + 4, y + th + 4), f"{pi/fps:.2f}s", fill=(230, 230, 230))
sheet.save(os.path.join(OUT, "0114a_抽帧拼图.jpg"), quality=88)
print(f"\n拼图已存: {OUT}\\0114a_抽帧拼图.jpg")

# ---------- 4. 音频抽取 ----------
wav = os.path.join(OUT, "audio_16k.wav")
subprocess.run([FFMPEG, "-y", "-i", SRC, "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "pcm_s16le", wav],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
print(f"\n音频抽取: {wav} 存在={os.path.exists(wav)}")

if os.path.exists(wav):
    import wave
    wf = wave.open(wav, "rb")
    sr = wf.getframerate()
    n = wf.getnframes()
    dur_a = n / sr
    data = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    wf.close()
    print(f"音频: sr={sr} 时长={dur_a:.3f}s 样本={n}")

    # 分窗 RMS（20ms hop）
    hop = int(sr * 0.02)
    win = int(sr * 0.05)
    rms = []
    for s in range(0, len(data) - win, hop):
        seg = data[s:s + win]
        rms.append(np.sqrt((seg ** 2).mean()))
    rms = np.array(rms)
    t_rms = np.arange(len(rms)) * hop / sr

    db = 20 * np.log10(rms + 1e-9)
    print(f"\n音频电平: 最大 {db.max():.1f}dB  中位 {np.median(db):.1f}dB  最小 {db.min():.1f}dB")

    # 语音段检测：阈值 = 中位数 + 8dB（自适应）
    thr = np.median(db) + 8.0
    active = db > thr
    # 形态学膨胀合并
    segs = []
    start = None
    for i, a in enumerate(active):
        if a and start is None:
            start = i
        elif not a and start is not None:
            if (i - start) * hop / sr > 0.15:
                segs.append((t_rms[start], t_rms[i]))
            start = None
    if start is not None:
        segs.append((t_rms[start], t_rms[-1]))

    print(f"\n=== 检测到 {len(segs)} 个发声段（阈值 {thr:.1f}dB）===")
    for i, (a, b) in enumerate(segs):
        m = (t_rms >= a) & (t_rms <= b)
        lvl = db[m].mean()
        print(f"  段{i+1}: {a:5.2f}s ~ {b:5.2f}s  ({(b-a):.2f}s, 均值 {lvl:.1f}dB)")
    gaps = []
    for i in range(1, len(segs)):
        gaps.append((segs[i][0] - segs[i-1][1], segs[i-1][1], segs[i][0]))
    if gaps:
        print("\n段间静默:")
        for g, e, s in gaps:
            print(f"  {e:5.2f}s ~ {s:5.2f}s  静默 {g:.2f}s")

    # 逐 0.25s 电平表
    print(f"\n=== 音频逐 0.25s 电平（dB）===")
    line = []
    for t in np.arange(0, dur_a, 0.25):
        m = (t_rms >= t) & (t_rms < t + 0.25)
        if m.sum():
            v = db[m].max()
            line.append(f"{t:5.2f}:{v:6.1f}")
    for i in range(0, len(line), 4):
        print("  " + "  ".join(line[i:i+4]))

    # 波形图
    fig_w, fig_h = 1000, 260
    wimg = Image.new("RGB", (fig_w, fig_h), (18, 18, 22))
    d2 = ImageDraw.Draw(wimg)
    mid = fig_h // 2
    px_per_s = fig_w / max(dur_a, 0.1)
    # 包络
    step_px = 2
    for x in range(0, fig_w, step_px):
        t0 = x / px_per_s
        t1 = (x + step_px) / px_per_s
        m = (t_rms >= t0) & (t_rms < t1)
        if m.sum() == 0:
            continue
        v = rms[m].max()
        h = min(int(v * 12 * (fig_h / 2)), fig_h // 2 - 4)
        d2.line([(x, mid - h), (x, mid + h)], fill=(90, 190, 140))
    d2.line([(0, mid), (fig_w, mid)], fill=(70, 70, 80))
    # 阈值线
    thr_lin = 10 ** (thr / 20)
    hy = int(thr_lin * 12 * (fig_h / 2))
    for x in range(0, fig_w, 6):
        d2.line([(x, mid - hy), (x + 3, mid - hy)], fill=(200, 90, 90))
    for s in [1, 2, 3, 4, 5, 6]:
        if s <= dur_a:
            x = int(s * px_per_s)
            d2.line([(x, 0), (x, fig_h)], fill=(60, 60, 72))
            d2.text((x + 3, 4), f"{s}s", fill=(150, 150, 160))
    wimg.save(os.path.join(OUT, "0114a_音频波形.png"))
    print(f"\n波形图: {OUT}\\0114a_音频波形.png")
