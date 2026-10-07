# -*- coding: utf-8 -*-
import os, cv2, numpy as np

src = r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容\0114a废弃.mp4"
out = r"D:\Aicomfyui\minimax3创作内容\重制版\废弃内容\_0114a分析"
os.makedirs(out, exist_ok=True)


def w(path, img):
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        print("encode fail", path)
        return
    buf.tofile(path)


cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
cap.release()
print("fps=%.2f n=%d dur=%.2f" % (fps, len(frames), len(frames) / fps))

# 关键时间点抽帧
times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 3.75, 4.0, 4.15, 4.25, 4.4, 4.6, 4.8, 5.0, 5.5, 6.0, 6.5]
sel = []
for t in times:
    i = min(int(t * fps), len(frames) - 1)
    sel.append(frames[i])
    w(os.path.join(out, "t%04d.jpg" % int(t * 100)), frames[i])

# 拼图 5 列
cols = 5
th = 240
tiles = []
for f in sel:
    h, ww = f.shape[:2]
    nw = int(ww * th / h)
    tiles.append(cv2.resize(f, (nw, th)))
maxw = max(t.shape[1] for t in tiles)
rowsn = (len(tiles) + cols - 1) // cols
canvas = np.zeros((rowsn * (th + 24), maxw * cols, 3), np.uint8)
for k, t in enumerate(tiles):
    r, c = divmod(k, cols)
    y = r * (th + 24)
    canvas[y:y + th, c * maxw:c * maxw + t.shape[1]] = t
    cv2.putText(canvas, "%.2fs" % times[k], (c * maxw + 5, y + th + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
w(os.path.join(out, "0114a_逐帧拼图.jpg"), canvas)
print("ok ->", out)
print("tiles:", len(tiles))
