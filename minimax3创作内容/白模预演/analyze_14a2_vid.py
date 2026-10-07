# -*- coding: utf-8 -*-
"""抽帧分析 0114a2 视频（临时文件名 940c...mp4）：检查转场/黑场、雾手搭肩、机位与露脸程度，并导出尾帧"""
import os, cv2, numpy as np
from PIL import Image

SRC = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\940c56f6-3d02-4300-9b31-687449923886.mp4"
OUTDIR = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\_0114a2分析"
TAILDIR = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\视频尾帧"
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(TAILDIR, exist_ok=True)

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
dur = n / fps
print(f"fps={fps:.2f}  帧数={n}  时长={dur:.2f}s")

frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
cap.release()
print("读取帧数:", len(frames))

def save(bgr, path, q=90):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb).save(path, quality=q)
    print("  保存:", path, os.path.getsize(path), "bytes")

def stat(f):
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return g.mean(), g.std()

rows = []
prev = None
for idx, f in enumerate(frames):
    m, s = stat(f)
    d = 0.0
    if prev is not None:
        d = np.abs(f.astype(np.float32) - prev.astype(np.float32)).mean()
    rows.append((idx / fps, m, s, d))
    prev = f

print("\n时间   亮度  细节度  帧间变化")
for t in np.arange(0, dur, 0.25):
    k = int(t * fps)
    if k < len(rows):
        tt, m, s, d = rows[k]
        flag = ""
        if m < 3: flag = "  <<< 近全黑"
        elif d > 18: flag = "  <<< 突变"
        print(f"{tt:5.2f}  {m:6.2f} {s:6.2f} {d:8.2f}{flag}")

mx = max(rows, key=lambda r: r[3])
print(f"\n最大帧间变化: t={mx[0]:.2f}s  变化={mx[3]:.2f}")
mn = min(rows, key=lambda r: r[1])
print(f"最暗帧: t={mn[0]:.2f}s  亮度={mn[1]:.2f}")

# 拼图
K = 16
idxs = np.linspace(0, len(frames) - 1, K).astype(int)
cols = 4
rowsn = int(np.ceil(K / cols))
th = 260
sample = frames[0]
tw = int(sample.shape[1] * th / sample.shape[0])
canvas = np.ones((rowsn * th, cols * tw, 3), np.uint8) * 20
for k, fi in enumerate(idxs):
    img = cv2.resize(frames[fi], (tw, th))
    r, c = divmod(k, cols)
    canvas[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = img
    cv2.putText(canvas, f"{fi/fps:.2f}s", (c * tw + 6, r * th + 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
save(canvas, os.path.join(OUTDIR, "0114a2_抽帧拼图.jpg"), 88)

# 最后1秒逐帧
last1 = frames[int(max(0, (dur - 1.0)) * fps):]
if last1:
    k2 = min(len(last1), 10)
    idx2 = np.linspace(0, len(last1) - 1, k2).astype(int)
    c2 = np.ones((th, k2 * tw, 3), np.uint8) * 20
    for k, fi in enumerate(idx2):
        c2[0:th, k * tw:(k + 1) * tw] = cv2.resize(last1[fi], (tw, th))
    save(c2, os.path.join(OUTDIR, "0114a2_最后1秒.jpg"), 88)

# 尾帧
best = max(frames[-5:], key=lambda f: cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
save(best, os.path.join(TAILDIR, "0114a2_tail.jpg"), 95)
save(best, os.path.join(OUTDIR, "0114a2_末帧.jpg"), 92)

# 尾帧人物占比量化
h, w = best.shape[:2]
print("\n尾帧尺寸:", w, "x", h)
g = cv2.cvtColor(best, cv2.COLOR_BGR2GRAY).astype(np.float32)
band = g[:, int(w * 0.30):int(w * 0.70)]
dark = (band < 60).sum(axis=1)
ys = np.where(dark > band.shape[1] * 0.10)[0]
ys2 = ys[(ys > int(h * 0.05)) & (ys < int(h * 0.92))]
if len(ys2):
    print("暗区(人物+椅) y:", ys2.min(), "-", ys2.max(), " 高=", ys2.max() - ys2.min(),
          "px  占画面高 %.1f%%" % (100 * (ys2.max() - ys2.min()) / h))
