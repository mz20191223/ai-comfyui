"""
《凌晨两点，Bug成精了》空灵声牵引 · 空景漂移推进 白模预演
----------------------------------------------------------
命题重定义：画面里没有走动的人物，是「镜头自身在空办公室里漂移推进」，
牵引力来自 Audio（权限魅影的空灵声音），最后在某个点「停住」。

与非之前"跟人走"方案的关键差别：
  - 镜头是自由的观察者，不受人步速（0.8~1.4 m/s）约束
  - 速度可按"飘"的质感自由设定（建议 0.8~1.2 m/s）
  - 推进感主要来自两侧近景物体的透视掠过，而非绝对位移量

运行：
  C:\\Python313\\python.exe previz_drift.py anim 4      # 4 秒版
  C:\\Python313\\python.exe previz_drift.py anim 3      # 3 秒版
  C:\\Python313\\python.exe previz_drift.py compare     # 多时长对比帧
"""
import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
OUT = r"D:\Aicomfyui\minimax3创作内容\白模预演\out_drift"
os.makedirs(OUT, exist_ok=True)
FPS = 25

# ============================ 场景 ============================
def _add_boxes(faces, cx, cy, cz, sx, sy, sz, color, _hx=None, _hy=None, _hz=None):
    """向 faces 追加一个 box 的 6 个面"""
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    q = [[(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
         [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)],
         [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
         [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
         [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
         [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)]]
    for quad in q:
        faces.append(([(cx + a * hx, cy + b * hy, cz + c * hz) for a, b, c in quad], color))


C_FLOOR, C_DESK, C_METAL, C_SCREEN = (202, 202, 204), (168, 164, 158), (132, 132, 138), (40, 40, 46)
C_KB, C_CHAIR, C_PART = (228, 228, 228), (126, 126, 132), (214, 214, 216)
C_CEIL = (222, 222, 224)

SCENE_STATIC = []
_add_boxes(SCENE_STATIC, 0, 0, -0.02, 16.0, 16.0, 0.04, C_FLOOR)
_add_boxes(SCENE_STATIC, 0, -4.6, 1.4, 16.0, 0.08, 2.8, C_PART)      # 远端墙
_add_boxes(SCENE_STATIC, -6.0, 0, 1.4, 0.08, 16.0, 2.8, C_PART)      # 左外墙
_add_boxes(SCENE_STATIC, 6.0, 0, 1.4, 0.08, 16.0, 2.8, C_PART)       # 右外墙


def workstation(cx, base_y, facing, screen_lit=False):
    f = facing
    parts = []
    _add_boxes(parts, cx, base_y, 0.75, 1.60, 0.72, 0.04, C_DESK)
    _add_boxes(parts, cx - 0.78, base_y, 0.375, 0.04, 0.68, 0.72, C_METAL)
    _add_boxes(parts, cx + 0.78, base_y, 0.375, 0.04, 0.68, 0.72, C_METAL)
    sy = base_y + 0.34 * f
    _add_boxes(parts, cx, sy, 0.90, 0.06, 0.05, 0.26, C_METAL)
    _add_boxes(parts, cx, sy + 0.06 * f, 1.12, 0.62, 0.03, 0.38,
               (60, 30, 34) if screen_lit else C_SCREEN)   # 红光屏/黑屏
    _add_boxes(parts, cx, base_y + 0.20 * f, 0.76 - 0.02 * f, 0.44, 0.15, 0.02, C_KB)
    cy_ = base_y - 0.62 * f
    _add_boxes(parts, cx, cy_, 0.46, 0.50, 0.50, 0.06, C_CHAIR)
    _add_boxes(parts, cx, cy_ - 0.24 * f, 0.78, 0.48, 0.06, 0.55, C_CHAIR)
    _add_boxes(parts, cx, cy_, 0.24, 0.08, 0.08, 0.42, C_METAL)
    _add_boxes(parts, cx, cy_, 0.03, 0.58, 0.58, 0.05, C_METAL)
    _add_boxes(parts, cx, base_y + 0.80 * f, 0.62, 1.66, 0.05, 1.24, C_PART)  # 隔断挡板
    return parts


def cluster(gx, base_y, facing, n=3, dx=2.25, lit_x=()):
    parts = []
    for i in range(n):
        cx = gx + (i - (n - 1) / 2.0) * dx
        k = round(cx, 2)
        parts += workstation(cx, base_y, facing, screen_lit=(k in lit_x))
    return parts


# 布局：两排工位（y=0 面朝 -Y；y=-3.4 面朝 +Y），中间通道 y≈-1.6，镜头沿 X 穿过通道
SCENE_STATIC += cluster(-2.9, 0.2, 1, 3, 2.25, lit_x=(-2.9,))
SCENE_STATIC += cluster(3.2, 0.2, 1, 3, 2.25)
SCENE_STATIC += cluster(-2.9, -3.4, 1, 3, 2.25)
SCENE_STATIC += cluster(3.2, -3.4, 1, 3, 2.25)


def sphere(cx, cy, cz, r, color, seg=8):
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


LIGHT = np.array([0.35, -0.62, 0.70])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
rng1 = np.random.default_rng(11)
N_MOTE = 200
MOTE_X = rng1.uniform(-0.15, 0.95, N_MOTE)   # 沿 X：0→1 对应路径 0→1
MOTE_S = rng1.uniform(-0.6, 1.0, N_MOTE)
MOTE_Z = rng1.uniform(0.0, 2.2, N_MOTE)
MOTE_P = rng1.uniform(0, 6.28, N_MOTE)


def smooth01(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


# 镜头漂移路径（关键：全场没有走动的人，只有镜头自己在飘）
# 起点 x=+3.6（通道入口），终点 x=-0.1（推到接近深处、雾将凝形处停住）
P_START = np.array([3.60, -1.55, 1.62])
P_END = np.array([-0.10, -1.35, 1.30])
PATH_LEN = float(np.linalg.norm(P_START[:2] - P_END[:2]))

TGT_START = np.array([-0.10, -1.55, 1.30])
TGT_END = np.array([-1.85, -1.15, 1.18])   # 视点略微转向声源所在的暗处


def cam_state(t, total, **kw):
    """返回 (cam_pos, target, focal_mm, vel_mps)"""
    u = np.clip(t / max(total, 1e-6), 0, 1)
    e = u * u * (3 - 2 * u)          # 整体 smoothstep：起步缓、末了缓 → 减速停住是"缓停"不是"硬停"
    pos = P_START + (P_END - P_START) * e
    tgt = TGT_START + (TGT_END - TGT_START) * smooth01(np.clip((u - 0.12) / 0.80, 0, 1))
    focal = kw.get("f0", 26) + (kw.get("f1", 24) - kw.get("f0", 26)) * e
    prev = P_START + (P_END - P_START) * smooth01(max(u - 0.008, 0))
    vel = float(np.linalg.norm((pos - prev)[:2])) / (0.008 * total)
    return pos, tgt, focal, abs(vel)


# ============================ 渲染 ============================
def render_scene(cam, tgt, focal, t, extra, label, hud=None, pe=0.0):
    C = np.array(cam, dtype=float)
    T = np.array(tgt, dtype=float)
    fwd = T - C
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right = right / np.linalg.norm(right)
    upv = np.cross(right, fwd)

    hfov = 2.0 * math.atan(18.0 / focal)
    fpx = (W / 2.0) / math.tan(hfov / 2.0)

    faces = list(SCENE_STATIC) + list(extra)
    img = Image.new("RGB", (W, H), (232, 232, 236))
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
        shade = 0.34 + 0.66 * max(0.0, float(np.dot(n, LIGHT)))
        items.append((sum(zs) / len(zs), [(int(round(a)), int(round(b))) for a, b in pts],
                      tuple(int(min(255, c * shade)) for c in color)))

    # 空气微粒 / 尘埃（给漂移感与体积感）
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(layer)
    for i in range(N_MOTE):
        ang = pe * 2.45
        mx = P_START[0] - ang + MOTE_X[i] * 1.9
        my = -1.55 + MOTE_S[i]
        mz = MOTE_Z[i] + 0.02 * math.sin(t * 1.4 + MOTE_P[i])
        pv = np.array([mx, my, mz]) - C
        z = float(np.dot(pv, fwd))
        if z <= 0.3 or z > 9.0:
            continue
        sx = W / 2.0 + fpx * float(np.dot(pv, right)) / z
        sy = H / 2.0 - fpx * float(np.dot(pv, upv)) / z
        r = max(1.0, fpx * 0.012 / z)
        a = int(np.clip(120 * (1 - z / 9.0), 0, 90))
        dd.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 255, 255, a))
    img = Image.alpha_composite(img.convert("RGBA"), layer)

    for _, pts, col in sorted(items, key=lambda x: -x[0]):
        ImageDraw.Draw(img).polygon(pts, fill=col, outline=(74, 74, 80))
    img = img.convert("RGB")

    d = ImageDraw.Draw(img)
    if label:
        d.rectangle([0, 0, W, 56], fill=(248, 248, 250))
        d.text((14, 12), label, fill=(25, 25, 30), font=FONT(24))
    if hud:
        yy = H - 128
        d.rectangle([0, yy - 10, W, H], fill=(248, 248, 250))
        for i, line in enumerate(hud):
            d.text((16, yy + i * 30), line, fill=(32, 32, 38), font=FONT(22))
    return img


def FONT(size=24):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ============================ 任务 ============================
def ghost_mass(t, total):
    """终点处的「未凝形的雾」——镜头停住时它就在那里，随推近逐渐显出轮廓"""
    u = np.clip(t / max(total, 1e-6), 0, 1)
    a = smooth01(np.clip((u - 0.35) / 0.65, 0, 1))
    g = []
    cx, cy = -1.95, -1.05
    _add_boxes(g, cx, cy, 0.30 + 0.06 * a, 0.30, 0.26, 0.60 + 0.10 * a, (74, 74, 86))
    g += sphere(cx, cy, 0.86 + 0.10 * a, 0.16, (96, 96, 108), seg=7)
    return g, a


def task_anim(total, f0=26, f1=24, tag=None):
    import cv2
    n = int(round(total * FPS))
    arr = []
    for i in range(n):
        t = i / FPS
        cam, tgt, focal, vel = cam_state(t, total, f0=f0, f1=f1)
        g, _ = ghost_mass(t, total)
        u = np.clip(t / max(total, 1e-6), 0, 1)
        pe = smooth01(u)
        moved = PATH_LEN * pe
        hud = ["%.0f 秒版｜漂移推进 %.2f / %.2f m" % (total, moved, PATH_LEN),
               "镜头速度 %.2f m/s   焦距 %.0f mm" % (vel, focal)]
        img = render_scene(cam, tgt, focal, t, g,
                           "空灵声牵引 · 空景漂移  t=%.2fs" % t, hud, pe=pe)
        arr.append(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
    name = tag or ("drift_%ds" % (int(total) if total == int(total) else total))
    p = os.path.join(OUT, name.replace(".", "_") + ".mp4")
    wr = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for f in arr:
        wr.write(f)
    wr.release()
    print("ANIM OK", p, len(arr))


def task_compare():
    for tt in (3.0, 4.0, 5.0, 6.0):
        cam, tgt, focal, vel = cam_state(tt * 0.5, tt)
        ts = np.linspace(0, tt, 121)
        vs = [cam_state(x, tt)[3] for x in ts]
        print("  %.0f 秒：路径 %.2f m  平均 %.2f m/s  峰值 %.2f m/s"
              % (tt, PATH_LEN, PATH_LEN / tt, max(vs)))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "compare":
        print("路径总长 %.2f m（通道入口 → 停止点）" % PATH_LEN)
        task_compare()
    elif cmd == "anim":
        tt = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
        task_anim(tt)
    else:
        task_anim(3.0)
        task_anim(4.0)
        task_anim(5.0)
