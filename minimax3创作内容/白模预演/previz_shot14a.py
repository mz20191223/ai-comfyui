"""
镜头14a 构图参考渲染：空办公室通道首帧 + 过客背影落幅
输出：out_shot14a/0114a_start.png（空景首帧）、0114a_end.png（落幅·过客背影中景）
"""
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
OUT = r"D:\Aicomfyui\minimax3创作内容\白模预演\out_shot14a"
os.makedirs(OUT, exist_ok=True)

C_FLOOR, C_DESK, C_METAL, C_SCREEN = (198, 198, 200), (166, 162, 156), (130, 130, 136), (38, 38, 44)
C_KB, C_CHAIR, C_PART = (226, 226, 226), (124, 124, 130), (212, 212, 214)
C_BODY, C_HEAD = (238, 234, 228), (244, 240, 234)
LIT = (58, 28, 32)

LIGHT = np.array([0.35, -0.62, 0.70])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def _add(faces, cx, cy, cz, sx, sy, sz, color):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    q = [[(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
         [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)],
         [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
         [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
         [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
         [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)]]
    for quad in q:
        faces.append(([(cx + a * hx, cy + b * hy, cz + c * hz) for a, b, c in quad], color))


def sphere(cx, cy, cz, r, color, seg=9):
    res = []

    def pt(i, j):
        th = math.pi * i / seg
        ph = 2 * math.pi * j / (seg * 2)
        return (cx + r * math.sin(th) * math.cos(ph),
                cy + r * math.sin(th) * math.sin(ph),
                cz + r * math.cos(th))
    for i in range(seg):
        for j in range(seg * 2):
            res.append(([pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)], color))
    return res


SCENE = []
_add(SCENE, 0, 0, -0.02, 16.0, 16.0, 0.04, C_FLOOR)
_add(SCENE, 0, -4.6, 1.4, 16.0, 0.08, 2.8, C_PART)     # 远端墙
_add(SCENE, -6.0, 0, 1.4, 0.08, 16.0, 2.8, C_PART)
_add(SCENE, 6.0, 0, 1.4, 0.08, 16.0, 2.8, C_PART)


def workstation(cx, base_y, facing, lit=False):
    f = facing
    p = []
    _add(p, cx, base_y, 0.75, 1.60, 0.72, 0.04, C_DESK)
    _add(p, cx - 0.78, base_y, 0.375, 0.04, 0.68, 0.72, C_METAL)
    _add(p, cx + 0.78, base_y, 0.375, 0.04, 0.68, 0.72, C_METAL)
    sy = base_y + 0.34 * f
    _add(p, cx, sy, 0.90, 0.06, 0.05, 0.26, C_METAL)
    _add(p, cx, sy + 0.06 * f, 1.12, 0.62, 0.03, 0.38, LIT if lit else C_SCREEN)
    _add(p, cx, base_y + 0.20 * f, 0.76, 0.44, 0.15, 0.02, C_KB)
    cy_ = base_y - 0.62 * f
    _add(p, cx, cy_, 0.46, 0.50, 0.50, 0.06, C_CHAIR)
    _add(p, cx, cy_ - 0.24 * f, 0.78, 0.48, 0.06, 0.55, C_CHAIR)
    _add(p, cx, cy_, 0.24, 0.08, 0.08, 0.42, C_METAL)
    _add(p, cx, cy_, 0.03, 0.58, 0.58, 0.05, C_METAL)
    _add(p, cx, base_y + 0.80 * f, 0.62, 1.66, 0.05, 1.24, C_PART)
    return p


def cluster(gx, base_y, n=3, dx=2.25, lit_x=()):
    p = []
    for i in range(n):
        cx = gx + (i - (n - 1) / 2.0) * dx
        p += workstation(cx, base_y, 1, lit=(round(cx, 2) in lit_x))
    return p


# 布局：y=0.2 排（镜头在通道 y=-1.55 看它 = 看到背影）、y=-3.4 排
SCENE += cluster(-2.9, 0.2, 3, 2.25, lit_x=(-2.9,))     # 过客所在排，他那台亮着
SCENE += cluster(3.2, 0.2, 3, 2.25)
SCENE += cluster(-2.9, -3.4, 3, 2.25)
SCENE += cluster(3.2, -3.4, 3, 2.25)


# ---- 坐姿过客（面朝 +Y=屏幕，镜头在 -Y 侧 → 背影）----
def human_sit():
    hip = 0.45
    p = []
    for sx in (-0.115, 0.115):
        _add(p, sx, 0.21, hip, 0.13, 0.44, 0.13, C_BODY)          # 大腿（水平）
        _add(p, sx, 0.42, hip - 0.22, 0.13, 0.13, 0.45, C_BODY)   # 小腿（垂直）
    _add(p, 0, 0, hip + 0.30, 0.42, 0.24, 0.60, C_BODY)           # 躯干
    for sx in (-0.255, 0.255):
        _add(p, sx, 0, hip + 0.24, 0.10, 0.12, 0.46, C_BODY)      # 上臂
        _add(p, sx, 0.10, hip - 0.02, 0.09, 0.10, 0.36, C_BODY)   # 前臂（搭桌）
    _add(p, 0, 0, hip + 0.665, 0.10, 0.10, 0.13, C_BODY)          # 颈
    p += sphere(0, 0, hip + 0.80, 0.118, C_HEAD, seg=9)
    return p


def place(local, px, py, yaw_deg=0.0):
    a = math.radians(yaw_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for verts, color in local:
        vv = [(px + (lx * ca - ly * sa), py + (lx * sa + ly * ca), lz) for (lx, ly, lz) in verts]
        out.append((vv, color))
    return out


GUOKE = place(human_sit(), -2.9, -0.42, 0.0)


def render(cam, tgt, focal, faces, label):
    C = np.array(cam, float)
    T = np.array(tgt, float)
    fwd = T - C
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right = right / np.linalg.norm(right)
    upv = np.cross(right, fwd)
    fpx = (W / 2.0) / math.tan(math.atan(18.0 / focal))

    img = Image.new("RGB", (W, H), (228, 228, 232))
    items = []
    for verts, color in faces:
        pts, zs, ok = [], [], True
        for p in verts:
            pv = np.array(p) - C
            z = float(np.dot(pv, fwd))
            if z <= 0.05:
                ok = False
                break
            pts.append((W / 2.0 + fpx * float(np.dot(pv, right)) / z,
                        H / 2.0 - fpx * float(np.dot(pv, upv)) / z))
            zs.append(z)
        if not ok:
            continue
        n = np.cross(np.array(verts[1]) - np.array(verts[0]), np.array(verts[2]) - np.array(verts[0]))
        nl = np.linalg.norm(n)
        if nl < 1e-9:
            continue
        n = n / nl
        cen = np.mean([np.array(p) for p in verts], axis=0)
        view = C - cen
        view = view / np.linalg.norm(view)
        if float(np.dot(n, view)) < 0:
            n = -n
        shade = 0.33 + 0.67 * max(0.0, float(np.dot(n, LIGHT)))
        items.append((sum(zs) / len(zs), [(int(round(a)), int(round(b))) for a, b in pts],
                      tuple(int(min(255, c * shade)) for c in color)))
    for _, pts, col in sorted(items, key=lambda x: -x[0]):
        ImageDraw.Draw(img).polygon(pts, fill=col, outline=(72, 72, 78))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 64], fill=(246, 246, 248))
    d.text((14, 14), label, fill=(25, 25, 30), font=FONT(24))
    return img


def FONT(size=24):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# 首帧：通道入口，过客仅在深处尽头的远景中（A 方案：人始终在场，推进=透视变化）
render((3.60, -1.55, 1.62), (-2.90, -1.00, 1.20), 26, SCENE + GUOKE,
       "0114a 首帧 0.0s｜通道深处·唯一亮屏+远景人影 26mm").save(os.path.join(OUT, "0114a_start.png"))
# 中帧：推进约一半（1.5s），过客已可辨认为坐姿背影
render((1.75, -1.45, 1.46), (-2.90, -0.71, 1.11), 38, SCENE + GUOKE,
       "0114a 中帧 1.5s｜同一条通道·人由小变大 38mm").save(os.path.join(OUT, "0114a_mid.png"))
# 落幅：过客背影中景
render((-0.10, -1.35, 1.30), (-2.90, -0.42, 1.02), 50, SCENE + GUOKE,
       "0114a_end 落幅 4.0s｜过客背影中景 50mm").save(os.path.join(OUT, "0114a_end.png"))

# 三格拼接对比：首帧 → 中帧 → 落幅（说明插值的是透视变化，不是人物生成）
a = Image.open(os.path.join(OUT, "0114a_start.png"))
b = Image.open(os.path.join(OUT, "0114a_mid.png"))
c = Image.open(os.path.join(OUT, "0114a_end.png"))
gap, pad = 18, 16
cw = (a.width * 3 + gap * 2 + pad * 2)
ch = a.height + pad * 2 + 46
canvas = Image.new("RGB", (cw, ch), (245, 245, 248))
d = ImageDraw.Draw(canvas)
d.text((pad, 12), "0114a 首帧→落幅衔接：人物全程在场，镜头沿同一条通道推进，插值的是透视放大",
       fill=(25, 25, 30), font=FONT(22))
x = pad
for im in (a, b, c):
    canvas.paste(im, (x, pad + 34))
    x += im.width + gap
canvas.save(os.path.join(OUT, "0114a_衔接三格.png"))
print("OK", OUT)
