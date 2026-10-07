"""
《凌晨两点，Bug成精了》第1集 镜头14 白模动态预演
------------------------------------------------
内容：过客愣神 → 身后冷笑 → 灰黑雾气从身后涌出绕过双肩包围 → 猛回头 → 定格
用途：验证「相机在后拉后能否看到回头时的惊愕神情」这一机位死结

坐标：地面 z=0，过客坐原点附近、面朝 +Y（屏幕在 +Y 侧），身后 = -Y 方向。单位米。
运行：
  C:\Python313\python.exe previz_shot14.py keys   # 关键帧 + 回头角度对比
  C:\Python313\python.exe previz_shot14.py anim   # 输出 mp4 动画
  C:\Python313\python.exe previz_shot14.py all
"""
import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
OUT = r"D:\Aicomfyui\minimax3创作内容\白模预演\out_shot14"
os.makedirs(OUT, exist_ok=True)

FPS = 25
TOTAL = 5.0

C_FLOOR, C_DESK, C_BODY, C_SCREEN = (205, 205, 205), (170, 166, 160), (242, 238, 232), (45, 45, 50)
C_METAL, C_KB, C_HEAD = (135, 135, 140), (232, 232, 232), (246, 242, 236)
FOG_RGB = (58, 58, 66)

LIGHT = np.array([0.45, -0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)

# ============================ 几何 ============================
SCENE_STATIC = []   # 不动的：地面/桌/显示器/椅/腿，[(verts, color)]


def box(cx, cy, cz, sx, sy, sz, color, out=None):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    q = [[(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
         [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)],
         [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
         [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
         [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
         [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)]]
    res = out if out is not None else []
    for quad in q:
        res.append(([(cx + a * hx, cy + b * hy, cz + c * hz) for a, b, c in quad], color))
    return res


def sphere_head_local(cx, cy, cz, r, color, seg=10):
    """返回局部坐标面列表（相对颈部枢轴）"""
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


# ---- 静态场景 ----
box(0, 0, -0.02, 6.0, 6.0, 0.04, C_FLOOR, SCENE_STATIC)
box(0, 0.375, 0.73, 1.60, 0.75, 0.04, C_DESK, SCENE_STATIC)
box(-0.78, 0.375, 0.365, 0.04, 0.70, 0.73, C_METAL, SCENE_STATIC)
box(0.78, 0.375, 0.365, 0.04, 0.70, 0.73, C_METAL, SCENE_STATIC)
box(0, 0.65, 0.76, 0.24, 0.18, 0.02, C_METAL, SCENE_STATIC)
box(0, 0.65, 0.90, 0.05, 0.05, 0.28, C_METAL, SCENE_STATIC)
box(0, 0.685, 1.10, 0.62, 0.03, 0.37, C_SCREEN, SCENE_STATIC)
box(0, 0.25, 0.76, 0.44, 0.15, 0.02, C_KB, SCENE_STATIC)
box(0.35, 0.25, 0.775, 0.06, 0.10, 0.03, C_KB, SCENE_STATIC)
box(0, -0.35, 0.45, 0.50, 0.50, 0.06, C_METAL, SCENE_STATIC)
box(0, -0.60, 0.72, 0.48, 0.06, 0.55, C_METAL, SCENE_STATIC)
box(0, -0.35, 0.21, 0.08, 0.08, 0.42, C_METAL, SCENE_STATIC)
box(0, -0.35, 0.02, 0.60, 0.60, 0.04, C_METAL, SCENE_STATIC)

# ---- 可动部件（局部坐标，绕各自枢轴 yaw 旋转）----
NECK_PIVOT = np.array([0.0, -0.15, 1.02])
HEAD_LOCAL = []
HEAD_LOCAL += box(0, 0, 0.04, 0.10, 0.10, 0.12, C_BODY)                 # 颈
HEAD_LOCAL += sphere_head_local(0, 0, 0.235, 0.115, C_HEAD, seg=9)      # 头
# 面部朝向标记：贴在脸前方、凸出球面，用来判断「回头后能不能看见五官」
HEAD_LOCAL += box(-0.050, 0.140, 0.255, 0.038, 0.014, 0.040, (55, 55, 65))   # 左眼位
HEAD_LOCAL += box(0.050, 0.140, 0.255, 0.038, 0.014, 0.040, (55, 55, 65))    # 右眼位
HEAD_LOCAL += box(0.000, 0.120, 0.238, 0.030, 0.014, 0.035, (55, 55, 65))    # 鼻（更贴近脸）

TORSO_PIVOT = np.array([0.0, -0.18, 0.76])
TORSO_LOCAL = []
TORSO_LOCAL += box(0, 0.02, 0.02, 0.44, 0.26, 0.62, C_BODY)             # 躯干
for sx in (-0.25, 0.25):
    TORSO_LOCAL += box(sx, -0.14, 0.14, 0.11, 0.11, 0.30, C_BODY)       # 上臂
for sx in (-0.22, 0.22):
    TORSO_LOCAL += box(sx, 0.05, -0.01, 0.10, 0.34, 0.10, C_BODY)       # 前臂
    TORSO_LOCAL += box(sx, 0.23, -0.01, 0.10, 0.12, 0.06, C_BODY)       # 手


def yaw_parts(local, pivot, yaw_deg):
    a = math.radians(yaw_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for verts, color in local:
        vv = []
        for p in verts:
            lx, ly, lz = p[0], p[1], p[2]
            rx = lx * ca - ly * sa
            ry = lx * sa + ly * ca
            vv.append((pivot[0] + rx, pivot[1] + ry, pivot[2] + lz))
        out.append((vv, color))
    return out


def rot_body(yaw_head, yaw_torso=0.0):
    return (yaw_parts(TORSO_LOCAL, TORSO_PIVOT, yaw_torso) +
            yaw_parts(HEAD_LOCAL, NECK_PIVOT, yaw_head))


# ============================ 雾 ============================
_SP = None


def fog_sprite(size=96):
    global _SP
    if _SP is None or _SP.size[0] != size:
        ax = np.linspace(-1, 1, size)
        gx, gy = np.meshgrid(ax, ax)
        g = np.exp(-(gx ** 2 + gy ** 2) * 2.6)
        a = (np.clip(g, 0, 1) * 255).astype(np.uint8)
        arr = np.zeros((size, size, 4), np.uint8)
        arr[:, :, 0] = FOG_RGB[0]
        arr[:, :, 1] = FOG_RGB[1]
        arr[:, :, 2] = FOG_RGB[2]
        arr[:, :, 3] = a
        _SP = Image.fromarray(arr, "RGBA")
    return _SP


rng = np.random.default_rng(7)
N_FOG = 260
FOG = []
for _ in range(N_FOG):
    rr0 = rng.uniform(0.55, 1.35)
    ang0 = math.pi + rng.uniform(-1.15, 1.15)          # 身后扇区（-Y）
    z0 = rng.uniform(0.10, 1.70)
    spread = rng.uniform(-0.9, 0.9) * math.pi          # 向两侧绕行
    ang1 = ang0 + math.copysign(min(abs(spread) + 1.4, math.pi * 0.95), spread if spread else 1)
    if abs(ang1 - math.pi) > math.pi:
        ang1 = ang1 - math.copysign(2 * math.pi, ang1)
    rr1 = rng.uniform(0.30, 0.72)
    z1 = z0 + rng.uniform(-0.15, 0.35)
    delay = rng.uniform(0.0, 0.55)
    FOG.append(dict(a0=ang0, r0=rr0, z0=z0, a1=ang1, r1=rr1, z1=z1,
                    delay=delay, rad=rng.uniform(0.10, 0.24), phase=rng.uniform(0, 6.28)))

BODY_C = np.array([0.0, -0.15, 0.95])


def fog_items(t, C, fwd, fpx, right, upv):
    """返回 [(depth, cx, cy, rpx, alpha)]"""
    p = np.clip((t - 1.6) / 2.6, 0.0, 1.0)
    if p <= 0:
        return []
    ease = p * p * (3 - 2 * p)
    out = []
    for f in FOG:
        q = np.clip((ease - f["delay"] * 0.45) / (1 - f["delay"] * 0.45 + 1e-6), 0, 1)
        if q <= 0:
            continue
        qe = q * q * (3 - 2 * q)
        ang = f["a0"] + (f["a1"] - f["a0"]) * qe
        rr = f["r0"] + (f["r1"] - f["r0"]) * qe
        zz = f["z0"] + (f["z1"] - f["z0"]) * qe + 0.05 * math.sin(t * 1.7 + f["phase"])
        x = rr * math.cos(ang)
        y = -0.15 + rr * math.sin(ang)
        pv = np.array([x, y, zz]) - C
        depth = float(np.dot(pv, fwd))
        if depth <= 0.08:
            continue
        sx = W / 2.0 + fpx * float(np.dot(pv, right)) / depth
        sy = H / 2.0 - fpx * float(np.dot(pv, upv)) / depth
        wr = f["rad"] * (0.55 + 0.9 * qe)
        rpx = fpx * wr / depth
        if rpx < 1.5:
            continue
        alpha = int(np.clip((0.16 + 0.42 * qe) * (0.7 + 0.3 * math.sin(f["phase"])), 0, 1) * 150)
        out.append((depth, sx, sy, rpx, alpha))
    return out


def draw_fog(items, size):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _, sx, sy, rpx, alpha in items:
        d.ellipse([sx - rpx, sy - rpx, sx + rpx, sy + rpx], fill=FOG_RGB + (alpha,))
    return layer


# ============================ 渲染 ============================
def render(cam_pos, target, focal_mm, t, yaw_head=0.0, yaw_torso=0.0, label=None):
    C = np.array(cam_pos, dtype=float)
    T = np.array(target, dtype=float)
    fwd = T - C
    fwd = fwd / np.linalg.norm(fwd)
    upv0 = np.array([0.0, 0.0, 1.0])
    right = np.cross(fwd, upv0)
    right = right / np.linalg.norm(right)
    upv = np.cross(right, fwd)

    hfov = 2.0 * math.atan(18.0 / focal_mm)
    fpx = (W / 2.0) / math.tan(hfov / 2.0)

    faces = list(SCENE_STATIC) + rot_body(yaw_head, yaw_torso)

    img = Image.new("RGB", (W, H), (238, 238, 240))
    d = ImageDraw.Draw(img)
    items = []
    for verts, color in faces:
        pts, zs = [], []
        ok = True
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
        v0, v1, v2 = map(np.array, verts[:3])
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
        items.append((sum(zs) / len(zs), [(int(round(a)), int(round(b))) for a, b in pts],
                      tuple(int(min(255, c * shade)) for c in color)))

    fogs = fog_items(t, C, fwd, fpx, right, upv)
    body_depth = float(np.dot(BODY_C - C, fwd))

    far_layer = draw_fog([f for f in fogs if f[0] > body_depth], (W, H))
    near_layer = draw_fog([f for f in fogs if f[0] <= body_depth], (W, H))

    img = Image.alpha_composite(img.convert("RGBA"), far_layer)
    for _, pts, col in sorted(items, key=lambda x: -x[0]):
        ImageDraw.Draw(img).polygon(pts, fill=col + (255,), outline=(70, 70, 75, 255))
    img = Image.alpha_composite(img, near_layer)
    img = img.convert("RGB")

    if label:
        ImageDraw.Draw(img).rectangle([0, 0, W, 62], fill=(250, 250, 252))
        ImageDraw.Draw(img).text((14, 16), label, fill=(25, 25, 30), font=FONT(24))
    return img


def FONT(size=24):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ============================ 机位方案 ============================
# A：严格按文档「开场13d脸部特写 + 只后拉/下沉」，相机始终在屏幕方向正前方
CAM_A = [
    (0.0, (0.00, 0.55, 1.25), (0.00, -0.15, 1.20), 85),   # 承接 13d（=04号机位）
    (1.6, (0.00, 0.50, 1.28), (0.00, -0.15, 1.18), 82),
    (5.0, (0.00, 0.30, 1.44), (0.00, -0.10, 1.06), 50),   # 后拉下沉，带出肩与身后
]
# B：后拉的同时向过客一侧弧移约 32°（连续运动，不切机位）——弧移方向必须与「回头方向」同侧
CAM_B = [
    (0.0, (0.00, 0.55, 1.25), (0.00, -0.15, 1.20), 85),
    (1.6, (-0.10, 0.52, 1.27), (-0.02, -0.15, 1.18), 82),
    (5.0, (-0.62, 0.34, 1.42), (-0.05, -0.10, 1.06), 52),
]
# C：弧移加大到约 55°，能看到更明确「朝身后看」的近侧脸
CAM_C = [
    (0.0, (0.00, 0.55, 1.25), (0.00, -0.15, 1.20), 85),
    (1.6, (-0.16, 0.52, 1.27), (-0.04, -0.15, 1.18), 82),
    (5.0, (-1.05, 0.30, 1.40), (-0.10, -0.08, 1.06), 50),
]


def cam_at(kf, t):
    for i in range(len(kf) - 1):
        t0, t1 = kf[i][0], kf[i + 1][0]
        if t <= t1 or i == len(kf) - 2:
            u = np.clip((t - t0) / (t1 - t0), 0, 1)
            a, b = kf[i], kf[i + 1]
            pos = tuple(a[1][k] + (b[1][k] - a[1][k]) * u for k in range(3))
            tgt = tuple(a[2][k] + (b[2][k] - a[2][k]) * u for k in range(3))
            fo = a[3] + (b[3] - a[3]) * u
            return pos, tgt, fo
    return kf[-1][1], kf[-1][2], kf[-1][3]


HEAD_KEY = [(3.2, 0.0), (4.3, None)]   # yaw 由调用方给定终值


def head_yaw(t, final):
    if t <= 3.2:
        return 0.0
    u = np.clip((t - 3.2) / 1.0, 0, 1)
    u = u * u * (3 - 2 * u)
    return final * u


# ============================ 任务 ============================
def task_keys():
    shots = [
        ("k1_t000_open.png", 0.0, CAM_A, 0, "t=0.0s  开场：承接13d 脸部特写 85mm"),
        ("k2_t260_fog.png", 2.6, CAM_A, 0, "t=2.6s  后拉中，雾从身后涌出、绕双肩向前"),
        ("k3_A_yaw100.png", 5.0, CAM_A, 100, "A 机位不动 + 回头100° → 背对镜头，看不到表情"),
        ("k4_A_yaw80.png", 5.0, CAM_A, 80, "A 机位不动 + 回头80° → 看得见侧脸，但不像回头"),
        ("k5_B_yaw125.png", 5.0, CAM_B, 125, "【推荐】B 弧移32° + 回头125° → 3/4侧脸，可见眼睛"),
        ("k6_C_yaw140.png", 5.0, CAM_C, 140, "C 弧移55° + 回头140° → 更明确朝身后看"),
    ]
    for name, t, kf, yaw, label in shots:
        cam, tgt, fo = cam_at(kf, t)
        img = render(cam, tgt, fo, t, yaw_head=head_yaw(t, yaw),
                     yaw_torso=head_yaw(t, yaw) * 0.35, label=label)
        img.save(os.path.join(OUT, name))
        print("saved", name, flush=True)


def task_anim():
    import cv2
    for tag, kf, yaw in (("A_机位不动_回头125", CAM_A, 125),
                         ("B_弧移32_回头125", CAM_B, 125),
                         ("C_弧移55_回头140", CAM_C, 140)):
        path = os.path.join(OUT, "shot14_%s.mp4" % tag)
        vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
        if not vw.isOpened():
            print("VideoWriter failed", path)
            continue
        n = int(TOTAL * FPS)
        for i in range(n):
            t = i / FPS
            cam, tgt, fo = cam_at(kf, t)
            img = render(cam, tgt, fo, t, yaw_head=head_yaw(t, yaw),
                         yaw_torso=head_yaw(t, yaw) * 0.35)
            arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            vw.write(arr)
        vw.release()
        print("saved", path, flush=True)


HEAD_CENTER = np.array([0.0, -0.15, 1.02 + 0.235])


def face_visibility(cam_pos, yaw_deg):
    """返回 cos 值：<0 脸朝向相机一侧；越接近 -1 越正面"""
    a = math.radians(yaw_deg)
    face = np.array([-math.sin(a), math.cos(a), 0.0])
    v = HEAD_CENTER - np.array(cam_pos, dtype=float)
    v = v / np.linalg.norm(v)
    return float(np.dot(face, v))


def verdict(c):
    if c < -0.35:
        return "正面偏斜·五官清楚"
    if c < -0.12:
        return "3/4侧脸·可见眼睛"
    if c < 0.06:
        return "正侧轮廓·眼睛勉强"
    return "背对镜头·看不见表情"


def task_diag():
    print("\n== 回头角度 × 机位方案：能不能看见「惊愕神情」（定格 t=5.0s）==")
    for tag, kf in (("A 机位不动(正前方后拉)", CAM_A),
                    ("B 弧移约32°", CAM_B),
                    ("C 弧移约55°", CAM_C)):
        cam, _, _ = cam_at(kf, 5.0)
        row = []
        for yaw in (60, 80, 100, 115, 125, 140, 160):
            c = face_visibility(cam, yaw)
            row.append("%d°:%.2f,%s" % (yaw, c, verdict(c)))
        print("\n[%s] 机位=%s" % (tag, tuple(round(x, 2) for x in cam)))
        for r in row:
            print("   ", r)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("diag", "all"):
        task_diag()
    if mode in ("keys", "all"):
        task_keys()
    if mode in ("anim", "all"):
        task_anim()
    print("DONE ->", OUT)
