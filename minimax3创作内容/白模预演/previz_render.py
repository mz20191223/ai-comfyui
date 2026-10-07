"""
工位白模机位预览渲染器（不依赖 Blender）
用途：《凌晨两点，Bug成精了》机位/构图验证（previz）。纯 Python 针孔相机投影 + Lambert 明暗。
坐标：地面 z=0，过客坐于原点附近、面朝 +Y，屏幕在 +Y 侧。单位米。
运行：C:\\Python313\\python.exe previz_render.py
"""
import os
import math
import numpy as np
from PIL import Image, ImageDraw

W, H = 720, 1280
OUT = r"D:\Aicomfyui\minimax3创作内容\白模预演\out_py"
os.makedirs(OUT, exist_ok=True)

C_FLOOR = (205, 205, 205)
C_DESK = (170, 166, 160)
C_BODY = (242, 238, 232)     # 过客：最亮
C_SCREEN = (45, 45, 50)      # 屏幕：深色
C_METAL = (135, 135, 140)
C_KB = (232, 232, 232)

LIGHT = np.array([0.45, -0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)

FACES = []   # [(顶点列表, 颜色)]


def add_box(cx, cy, cz, sx, sy, sz, color):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    def v(a, b, c):
        return (cx + a * hx, cy + b * hy, cz + c * hz)
    quads = [
        [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
        [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)],
        [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
        [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
        [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
        [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)],
    ]
    for q in quads:
        FACES.append(([v(*p) for p in q], color))


def add_sphere(cx, cy, cz, r, color, seg=10):
    def pt(i, j):
        theta = math.pi * i / seg          # 0..pi
        phi = 2 * math.pi * j / (seg * 2)
        return (cx + r * math.sin(theta) * math.cos(phi),
                cy + r * math.sin(theta) * math.sin(phi),
                cz + r * math.cos(theta))
    for i in range(seg):
        for j in range(seg * 2):
            FACES.append(([pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)], color))


# ---------- 地面 ----------
add_box(0, 0, -0.02, 6.0, 6.0, 0.04, C_FLOOR)

# ---------- 桌子（桌面 z=0.75，深 0.75，宽 1.6） ----------
add_box(0, 0.375, 0.73, 1.60, 0.75, 0.04, C_DESK)
add_box(-0.78, 0.375, 0.365, 0.04, 0.70, 0.73, C_METAL)
add_box(0.78, 0.375, 0.365, 0.04, 0.70, 0.73, C_METAL)

# ---------- 显示器（屏幕朝 -Y，正对过客） ----------
add_box(0, 0.65, 0.76, 0.24, 0.18, 0.02, C_METAL)
add_box(0, 0.65, 0.90, 0.05, 0.05, 0.28, C_METAL)
add_box(0, 0.685, 1.10, 0.62, 0.03, 0.37, C_SCREEN)

# ---------- 键鼠 ----------
add_box(0, 0.25, 0.76, 0.44, 0.15, 0.02, C_KB)
add_box(0.35, 0.25, 0.775, 0.06, 0.10, 0.03, C_KB)

# ---------- 椅子 ----------
add_box(0, -0.35, 0.45, 0.50, 0.50, 0.06, C_METAL)
add_box(0, -0.60, 0.72, 0.48, 0.06, 0.55, C_METAL)
add_box(0, -0.35, 0.21, 0.08, 0.08, 0.42, C_METAL)
add_box(0, -0.35, 0.02, 0.60, 0.60, 0.04, C_METAL)

# ---------- 过客（坐姿，面朝 +Y） ----------
add_box(0, -0.18, 0.76, 0.44, 0.26, 0.62, C_BODY)      # 躯干
add_box(0, -0.15, 1.10, 0.10, 0.10, 0.10, C_BODY)      # 颈
add_sphere(0, -0.15, 1.20, 0.115, C_BODY)              # 头（眼高约 1.20）
for sx in (-0.12, 0.12):
    add_box(sx, 0.10, 0.55, 0.16, 0.45, 0.14, C_BODY)  # 大腿
    add_box(sx, 0.32, 0.25, 0.14, 0.14, 0.45, C_BODY)  # 小腿
    add_box(sx, 0.42, 0.03, 0.12, 0.25, 0.06, C_BODY)  # 脚
for sx in (-0.25, 0.25):
    add_box(sx, -0.14, 0.92, 0.11, 0.11, 0.30, C_BODY)  # 上臂
for sx in (-0.22, 0.22):
    add_box(sx, 0.05, 0.79, 0.10, 0.34, 0.10, C_BODY)   # 前臂
    add_box(sx, 0.23, 0.79, 0.10, 0.12, 0.06, C_BODY)   # 手


def render(cam_pos, target, focal_mm, out_name):
    C = np.array(cam_pos, dtype=float)
    T = np.array(target, dtype=float)
    fwd = T - C
    fwd = fwd / np.linalg.norm(fwd)
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(fwd, up)
    right = right / np.linalg.norm(right)
    upv = np.cross(right, fwd)

    hfov = 2.0 * math.atan(18.0 / focal_mm)          # 传感器宽 36mm
    fpx = (W / 2.0) / math.tan(hfov / 2.0)

    img = Image.new("RGB", (W, H), (238, 238, 240))
    d = ImageDraw.Draw(img)
    items = []

    for verts, color in FACES:
        pts, zs = [], []
        ok = True
        for p in verts:
            pv = np.array(p) - C
            z = float(np.dot(pv, fwd))
            if z <= 0.05:
                ok = False
                break
            x = W / 2.0 + fpx * float(np.dot(pv, right)) / z
            y = H / 2.0 - fpx * float(np.dot(pv, upv)) / z
            pts.append((x, y))
            zs.append(z)
        if not ok:
            continue
        v0 = np.array(verts[0])
        v1 = np.array(verts[1])
        v2 = np.array(verts[2])
        n = np.cross(v1 - v0, v2 - v0)
        nl = np.linalg.norm(n)
        if nl < 1e-9:
            continue
        n = n / nl
        cen = np.mean([np.array(p) for p in verts], axis=0)
        view = C - cen
        view = view / np.linalg.norm(view)
        if float(np.dot(n, view)) < 0:
            n = -n
        shade = 0.38 + 0.62 * max(0.0, float(np.dot(n, LIGHT)))
        col = tuple(int(min(255, c * shade)) for c in color)
        items.append((sum(zs) / len(zs), [(int(round(a)), int(round(b))) for a, b in pts], col))

    items.sort(key=lambda t: -t[0])                   # 远 → 近
    for _, pts, col in items:
        d.polygon(pts, fill=col, outline=(70, 70, 75))

    path = os.path.join(OUT, out_name)
    img.save(path)
    print("saved", out_name, flush=True)
    return path


SHOTS = [
    ("01_wide_3q.png", (1.80, -1.40, 1.55), (0, 0.20, 0.85), 35),
    ("02_side_mid.png", (1.70, 0.35, 1.30), (0, 0.15, 0.95), 50),
    ("03_front_50mm.png", (0.00, 0.55, 1.25), (0, -0.15, 1.20), 50),
    ("04_front_85mm.png", (0.00, 0.55, 1.25), (0, -0.15, 1.20), 85),
    ("05_screen_13c.png", (0.42, -0.02, 1.32), (0, 0.685, 1.08), 35),
    ("06_over_shoulder.png", (0.55, -0.75, 1.42), (0, 0.60, 1.05), 40),
    ("07_keyboard_top.png", (0.85, -0.25, 1.30), (0, 0.22, 0.77), 50),
    ("08_pov_screen.png", (0.00, -0.15, 1.20), (0, 0.685, 1.10), 35),
    ("09_top_layout.png", (0.02, 0.02, 3.20), (0.02, 0.12, 0.00), 28),
]

for name, cam, tgt, focal in SHOTS:
    render(cam, tgt, focal, name)

print("ALL DONE ->", OUT)
