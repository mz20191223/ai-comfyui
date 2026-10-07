# -*- coding: utf-8 -*-
import cv2, numpy as np

pa = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\0114aend.jpg"
pb = r"D:\Aicomfyui\minimax3创作内容\重制版\分镜图\0114b.jpg"
ia = cv2.imdecode(np.fromfile(pa, dtype=np.uint8), cv2.IMREAD_COLOR)
ib = cv2.imdecode(np.fromfile(pb, dtype=np.uint8), cv2.IMREAD_COLOR)
print("a:", ia.shape[1], "x", ia.shape[0])
print("b:", ib.shape[1], "x", ib.shape[0])

orb = cv2.ORB_create(3000)
ga = cv2.cvtColor(ia, cv2.COLOR_BGR2GRAY)
gb = cv2.cvtColor(ib, cv2.COLOR_BGR2GRAY)
ka, da = orb.detectAndCompute(ga, None)
kb, db = orb.detectAndCompute(gb, None)
print("kps:", len(ka), len(kb))
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
m = bf.match(da, db)
m = sorted(m, key=lambda x: x.distance)[:400]
print("matches:", len(m), " best dist:", m[0].distance if m else None)

if len(m) > 20:
    src = np.float32([ka[mm.queryIdx].pt for mm in m]).reshape(-1, 1, 2)
    dst = np.float32([kb[mm.queryIdx].pt for mm in m]).reshape(-1, 1, 2)
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    if M is not None:
        scale = np.sqrt(M[0, 0] ** 2 + M[1, 0] ** 2)
        ang = np.degrees(np.arctan2(M[1, 0], M[0, 0]))
        tx, ty = M[0, 2], M[1, 2]
        print("inliers:", int(inl.sum()) if inl is not None else "?")
        print("scale(a->b) = %.3f   rot = %.2f deg   t = (%.1f, %.1f)" % (scale, ang, tx, ty))
        print("=> 0114aend 放大 %.2f 倍可达到 0114b 的景别" % scale)
    else:
        print("affine estimate failed")
else:
    print("not enough matches")

# 亮度剖面（垂直方向）与雾（亮区）分布
for name, im in [("0114aend", ia), ("0114b", ib)]:
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    h, w = g.shape
    prof = g.mean(axis=1)
    q = [int(np.percentile(np.arange(h), p, weights=np.maximum(prof - prof.min(), 1e-6)))
         for p in (10, 50, 90)]
    print("\n%s 亮度重心分布(10/50/90%%): %s (画面高 %d)" % (name, q, h))
    bright = (g > np.percentile(g, 90)).mean() * 100
    print("%s 高亮像素占比: %.1f%%  平均亮度 %.1f" % (name, bright, g.mean()))
