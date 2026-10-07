# -*- coding: utf-8 -*-
"""细看 3.2-4.4s 过渡段 + 末帧落幅人物占比"""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw

SRC = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\0114a.mp4"
OUT = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜视频\_0114a分析"

cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
cap.release()
fps = fps or 24.0

# ---- A. 过渡段 3.2~4.4s 每 0.1s 一帧 ----
picks = [int(t * fps) for t in np.arange(3.2, 4.45, 0.1)]
picks = [p for p in picks if p < len(frames)]
tw, th = frames[0].shape[1] // 4, frames[0].shape[0] // 4
cols = 4
rows_n = (len(picks) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows_n * (th + 22)), (20, 20, 20))
dr = ImageDraw.Draw(sheet)
for k, pi in enumerate(picks):
    img = Image.fromarray(cv2.cvtColor(frames[pi], cv2.COLOR_BGR2RGB)).resize((tw, th))
    r, c = divmod(k, cols)
    sheet.paste(img, (c * tw, r * (th + 22)))
    dr.text((c * tw + 4, r * (th + 22) + th + 4), f"{pi/fps:.2f}s", fill=(230, 230, 230))
sheet.save(os.path.join(OUT, "0114a_过渡段3.2-4.4s.jpg"), quality=90)
print("过渡段拼图 OK")

# ---- B. 末帧人物占比（暗部主体检测：红光区域 + 人形剪影）----
def person_height_ratio(f):
    """估计人物(含椅)占画面高度比例：找暗背景中偏亮的主体连通域"""
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    # 主体 = 中间 60% 区域内、亮度高于背景中位数的像素
    roi = g[:, int(w*0.2):int(w*0.8)]
    med = np.median(roi)
    mask = (roi > med + 12).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return 0.0, None
    c = max(cnts, key=cv2.contourArea)
    x, y, cw, ch = cv2.boundingRect(c)
    return ch / h, (x + int(w*0.2), y, cw, ch)

print("\n=== 人物占比估计（末帧附近）===")
for t in [4.5, 5.0, 5.5, 6.0, 6.3, 6.5]:
    i = min(int(t * fps), len(frames) - 1)
    ratio, box = person_height_ratio(frames[i])
    print(f"  {t:.1f}s: 主体高度占画面 {ratio*100:.0f}%  box={box}")

# 末帧保存
last = frames[-1]
Image.fromarray(cv2.cvtColor(last, cv2.COLOR_BGR2RGB)).save(
    os.path.join(OUT, "0114a_末帧.jpg"), quality=92)
print("\n末帧已存: 0114a_末帧.jpg")
