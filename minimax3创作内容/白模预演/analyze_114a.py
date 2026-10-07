# -*- coding: utf-8 -*-
import os, cv2, numpy as np

src = r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容\0114a废弃.mp4"
out = r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容\_0114a分析"
os.makedirs(out, exist_ok=True)

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
dur = n / fps if fps else 0
print("fps=%.3f frames=%d dur=%.3f" % (fps, n, dur))

frames = []
idx = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
    idx += 1
cap.release()
print("read", len(frames))

# 统一缩放，便于计算与拼图
small = [cv2.resize(f, (192, 340), interpolation=cv2.INTER_AREA) for f in frames]
gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in small]

# 相邻帧差异（隔 1 帧）
step = max(1, int(round(fps * 0.25)))
print("\n=== t(s) | MAD(prev) | MAD(first) | meanLuma | blur(var of Laplacian) ===")
rows = []
prev = None
for i in range(0, len(gray), step):
    g = gray[i]
    t = i / fps
    mad_prev = float(np.mean(np.abs(g - gray[i - step]))) if i >= step else 0.0
    mad_first = float(np.mean(np.abs(g - gray[0])))
    luma = float(np.mean(g))
    lap = float(cv2.Laplacian(gray[i].astype(np.uint8), cv2.CV_64F).var())
    rows.append((t, mad_prev, mad_first, luma, lap))
    print("%5.2f | %8.3f | %9.3f | %8.2f | %8.1f" % (t, mad_prev, mad_first, luma, lap))

# 抽帧存图（每 0.5 秒）
saved = []
for k, t in enumerate([i * 0.5 for i in range(int(dur / 0.5) + 1)]):
    i = min(int(t * fps), len(frames) - 1)
    p = os.path.join(out, "t%03d.jpg" % int(t * 10))
    cv2.imwrite(p, frames[i])
    saved.append(p)
print("\nsaved", len(saved), "frames ->", out)

# 拼图 4 列
sel = [frames[min(int(t * fps), len(frames) - 1)] for t in [0, 1, 2, 3, 4, 5, 5.5]]
cols = 4
rowsn = (len(sel) + cols - 1) // cols
th = 320
tiles = []
for f in sel:
    h, w = f.shape[:2]
    nw = int(w * th / h)
    tiles.append(cv2.resize(f, (nw, th)))
maxw = max(t.shape[1] for t in tiles)
canvas_h = rowsn * (th + 26)
canvas = np.zeros((canvas_h, maxw * cols, 3), np.uint8)
for k, t in enumerate(tiles):
    r, c = divmod(k, cols)
    y = r * (th + 26)
    canvas[y:y + th, c * maxw:c * maxw + t.shape[1]] = t
    cv2.putText(canvas, "%.1fs" % [0, 1, 2, 3, 4, 5, 5.5][k], (c * maxw + 6, y + th + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
cv2.imwrite(os.path.join(out, "0114a_逐秒拼图.jpg"), canvas)
print("grid ->", os.path.join(out, "0114a_逐秒拼图.jpg"))
