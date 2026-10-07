# -*- coding: utf-8 -*-
"""抽帧分析 0114a1.mp4：检测转场/黑场、看推进是否连续，并导出尾帧 0114a1_tail.jpg"""
import os, cv2, numpy as np
from PIL import Image

SRC = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\0114a1.mp4"
OUTDIR = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\_0114a1分析"
TAILDIR = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\视频尾帧"
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(TAILDIR, exist_ok=True)

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
dur = n / fps
print(f"fps={fps:.2f}  帧数={n}  时长={dur:.2f}s")

frames = []
i = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
    i += 1
cap.release()
print("读取帧数:", len(frames))

def save(bgr, path, q=90):
    """用 PIL 存，避免 cv2.imwrite 不支持中文路径（会静默失败）"""
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

# 打印每秒
print("\n时间   亮度  细节度  帧间变化")
for t in np.arange(0, dur, 0.25):
    k = int(t * fps)
    if k < len(rows):
        tt, m, s, d = rows[k]
        flag = ""
        if m < 3: flag = "  <<< 近全黑"
        elif d > 18: flag = "  <<< 突变"
        print(f"{tt:5.2f}  {m:6.2f} {s:6.2f} {d:8.2f}{flag}")

# 找最大帧间变化
mx = max(rows, key=lambda r: r[3])
print(f"\n最大帧间变化: t={mx[0]:.2f}s  变化={mx[3]:.2f}")

# 找最暗
mn = min(rows, key=lambda r: r[1])
print(f"最暗帧: t={mn[0]:.2f}s  亮度={mn[1]:.2f}")

# 拼图（16 帧）
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
save(canvas, os.path.join(OUTDIR, "0114a1_抽帧拼图.jpg"), 88)

# 尾帧：取最后 3 帧里最清晰的一张（细节度最高）
tail_candidates = frames[-5:]
best = max(tail_candidates, key=lambda f: cv2.Laplacian(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
tail_path = os.path.join(TAILDIR, "0114a1_tail.jpg")
save(best, tail_path, 95)
print("\n尾帧已导出:", tail_path, best.shape)

# 末帧单独存一份大图便于查看
save(best, os.path.join(OUTDIR, "0114a1_末帧.jpg"), 92)

# 最后 1 秒逐帧（看是否定格）
last = frames[int(max(0, (dur - 1.2)) * fps):]
if len(last) > 0:
    step = max(1, len(last) // 8)
    sel = last[::step][:8]
    tw2 = int(sample.shape[1] * 200 / sample.shape[0])
    c2 = np.ones((200 * 2, tw2 * 4, 3), np.uint8) * 20
    for k, f in enumerate(sel[:8]):
        img = cv2.resize(f, (tw2, 200))
        r, c = divmod(k, 4)
        c2[r * 200:(r + 1) * 200, c * tw2:(c + 1) * tw2] = img
    save(c2, os.path.join(OUTDIR, "0114a1_最后1秒.jpg"), 88)

print("分析图目录:", OUTDIR)
