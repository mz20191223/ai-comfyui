# -*- coding: utf-8 -*-
import os, cv2, numpy as np

p = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\0114aend.jpg"
img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
h, w = img.shape[:2]
print("size:", w, "x", h, " ratio=%.3f" % (w / h))
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print("mean luma: %.2f  std: %.2f" % (gray.mean(), gray.std()))

# 1) 3x3 分块亮度
print("\n--- 3x3 分块平均亮度 ---")
for r in range(3):
    row = []
    for c in range(3):
        blk = gray[r * h // 3:(r + 1) * h // 3, c * w // 3:(c + 1) * w // 3]
        row.append("%6.1f" % blk.mean())
    print(" ".join(row))

# 2) 长直线检测（拼贴网格 / 规范稿分割线）
edges = cv2.Canny(gray, 50, 150, apertureSize=3)
lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=int(min(w, h) * 0.35),
                        minLineLength=int(min(w, h) * 0.35), maxLineGap=8)
print("\n--- 长直线（>=35%短边，拼贴分割线嫌疑） ---")
if lines is None:
    print("无")
else:
    horiz, vert = [], []
    for l in lines[:, 0]:
        x1, y1, x2, y2 = l
        if abs(y2 - y1) < 6:
            horiz.append((y1, x2 - x1))
        elif abs(x2 - x1) < 6:
            vert.append((x1, y2 - y1))
    print("水平线 %d 条: %s" % (len(horiz), sorted(horiz)[:12]))
    print("垂直线 %d 条: %s" % (len(vert), sorted(vert)[:12]))

# 3) 色彩统计（红警报占比 / 冷绿 / 青灰）
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
red = ((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 168)) & (hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 50)
green = (hsv[:, :, 0] > 40) & (hsv[:, :, 0] < 85) & (hsv[:, :, 1] > 50) & (hsv[:, :, 2] > 40)
print("\n--- 色彩占比 ---")
print("强红像素: %.2f%%" % (red.mean() * 100))
print("明显绿像素: %.2f%%" % (green.mean() * 100))
print("饱和度均值: %.1f  明度均值: %.1f" % (hsv[:, :, 1].mean(), hsv[:, :, 2].mean()))

# 4) 中央“人物暗块”估计：以中轴列带 vs 两侧列带 的亮度差定位人物竖直范围
col_mid = gray[:, int(w * 0.30):int(w * 0.70)].mean(axis=1)
col_side = np.hstack([gray[:, :int(w * 0.15)], gray[:, int(w * 0.85):]]).mean(axis=1)
diff = col_mid - col_side  # 负=中轴比两侧暗（背光人影）
sm = np.convolve(diff, np.ones(15) / 15, mode="same")
thr = sm.min() * 0.45
mask = sm < thr
ys = np.where(mask)[0]
if len(ys) > 0:
    top, bot = ys[0], ys[-1]
    print("\n--- 中轴暗块（疑似人物背影） ---")
    print("竖直范围: %.1f%% ~ %.1f%%  (高度占画面 %.1f%%)" %
          (top / h * 100, bot / h * 100, (bot - top) / h * 100))
else:
    print("\n未检测到明显中轴暗块")

# 5) 高频细节密度（规范稿文字/色卡会带来局部高频）
lap = cv2.Laplacian(gray, cv2.CV_64F).var()
print("\nLaplacian 方差(细节密度): %.1f" % lap)
# 上/中/下 三段细节密度
for name, sl in [("上1/3", slice(0, h // 3)), ("中1/3", slice(h // 3, 2 * h // 3)), ("下1/3", slice(2 * h // 3, h))]:
    print("  %s: %.1f" % (name, cv2.Laplacian(gray[sl], cv2.CV_64F).var()))
