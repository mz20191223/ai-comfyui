"""
《凌晨两点，Bug成精了》循声追踪短镜 · 白模动态预演
------------------------------------------------
验证命题：3~4 秒能否完成「听着权限魅影的声音一路追过去、到魅影前停住」的一镜到底

坐标：地面 z=0，过客起点在工位椅子上（原点附近），面朝 +Y。
      魅影/声源在左后方深处。单位米。

运行：
  C:\\Python313\\python.exe previz_track.py anim   # 输出 3s / 4s 两版 mp4
  C:\\Python313\\python.exe previz_track.py keys   # 关键帧
  C:\\Python313\\python.exe previz_track.py budget # 打印运动预算
"""
import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
OUT = r"D:\Aicomfyui\minimax3创作内容\白模预演\out_track"
os.makedirs(OUT, exist_ok=True)

FPS = 25

C_FLOOR, C_DESK, C_BODY, C_SCREEN = (205, 205, 205), (170, 166, 160), (242, 238, 232), (45, 45, 50)
C_METAL, C_KB, C_HEAD = (135, 135, 140), (232, 232, 232), (246, 242, 236)
C_GHOST = (70, 70, 82)

LIGHT = np.array([0.45, -0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


# ============================ 几何基元 ============================
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


# ============================ 静态场景 ============================
SCENE_STATIC = []
box(0, 0, -0.02, 8.0, 8.0, 0.04, C_FLOOR, SCENE_STATIC)          # 地面
box(0, 0.375, 0.73, 1.60, 0.75, 0.04, C_DESK, SCENE_STATIC)      # 桌面
box(-0.78, 0.375, 0.365, 0.04, 0.70, 0.73, C_METAL, SCENE_STATIC)
box(0.78, 0.375, 0.365, 0.04, 0.70, 0.73, C_METAL, SCENE_STATIC)
box(0, 0.685, 1.10, 0.62, 0.03, 0.37, C_SCREEN, SCENE_STATIC)    # 显示器
box(0, 0.65, 0.90, 0.05, 0.05, 0.28, C_METAL, SCENE_STATIC)
box(0, 0.25, 0.76, 0.44, 0.15, 0.02, C_KB, SCENE_STATIC)         # 键盘
box(0, -0.35, 0.45, 0.50, 0.50, 0.06, C_METAL, SCENE_STATIC)     # 椅座
box(0, -0.60, 0.72, 0.48, 0.06, 0.55, C_METAL, SCENE_STATIC)     # 椅背
box(0, -0.35, 0.02, 0.60, 0.60, 0.04, C_METAL, SCENE_STATIC)

# 远处的隔断/机柜，给纵深参照
box(-2.6, 1.6, 0.75, 1.2, 0.06, 1.5, (188, 188, 190), SCENE_STATIC)
box(2.8, 1.4, 0.70, 1.0, 0.06, 1.4, (188, 188, 190), SCENE_STATIC)

# 墙（左后方深处），魅影在墙前
box(-3.4, -1.0, 1.4, 0.08, 5.0, 2.8, (216, 216, 218), SCENE_STATIC)

# 声源/魅影（终点）：暗处一团 Tall mass
GHOST_POS = (-1.95, -1.55, 0.0)
GHOST = []
box(GHOST_POS[0], GHOST_POS[1], 0.55, 0.34, 0.30, 1.10, C_GHOST, GHOST)
box(GHOST_POS[0], GHOST_POS[1], 1.22, 0.26, 0.26, 0.26, C_GHOST, GHOST)
sphere(GHOST_POS[0], GHOST_POS[1], 1.24, 0.13, (95, 95, 105), seg=8)


# ============================ 人体（坐姿↔站姿插值） ============================
def segs(a, b, u):
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(len(a)))


def human_local(s, phase=0.0):
    """s=0 坐姿，s=1 站姿。局部坐标：原点在脚底中心，面朝 +Y，单位米。返回 (faces, head_center)"""
    hip = 0.45 + 0.48 * s
    # 腿
    upper = segs((0.00, 0.21, hip, 0.13, 0.44, 0.13), (0.00, 0.005, 0.235, 0.13, 0.13, 0.47), s)
    lower = segs((0.00, 0.42, hip - 0.22, 0.13, 0.13, 0.45), (0.00, 0.005, 0.70, 0.13, 0.13, 0.47), s)
    faces = []
    for sx in (-0.115, 0.115):
        for prm in (upper, lower):
            box(sx + 0.0, prm[1], prm[2], prm[3], prm[4], prm[5], C_BODY, faces)
    # 躯干
    box(0, 0, hip + 0.30, 0.42, 0.24, 0.60, C_BODY, faces)
    # 手臂（走路摆动）
    swing = 0.20 * math.sin(phase) * s
    for sx in (-0.255, 0.255):
        box(sx, 0.02 * s, hip + 0.24, 0.10, 0.12, 0.46, C_BODY, faces)
        box(sx, swing, hip - 0.02, 0.09, 0.10, 0.40, C_BODY, faces)
    # 颈/头
    box(0, 0, hip + 0.665, 0.10, 0.10, 0.13, C_BODY, faces)
    head_z = hip + 0.80
    faces += sphere(0, 0, head_z, 0.118, C_HEAD, seg=9)
    # 面部朝向标记（凸出球面，朝 +Y）
    box(-0.050, 0.130, head_z + 0.015, 0.036, 0.014, 0.038, (55, 55, 65), faces)
    box(0.050, 0.130, head_z + 0.015, 0.036, 0.014, 0.038, (55, 55, 65), faces)
    box(0.000, 0.112, head_z + 0.005, 0.030, 0.014, 0.034, (55, 55, 65), faces)
    return faces, head_z


def place_body(faces_local, px, py, yaw_deg):
    a = math.radians(yaw_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for verts, color in faces_local:
        vv = []
        for (lx, ly, lz) in verts:
            rx = lx * ca - ly * sa
            ry = lx * sa + ly * ca
            vv.append((px + rx, py + ry, lz))
        out.append((vv, color))
    return out


# ============================ 运动曲线 ============================
START = np.array([0.30, 0.10])     # 起身后站位
END = np.array([-1.45, -1.25])     # 在魅影前约 0.7m 停住
TOTAL_DIST = float(np.linalg.norm(END - START))

# 三个节拍的时间占比（相对总时长）
T_REACT = 0.42      # 反应+转头（相对秒，绝对值偏短，受时长缩放影响）
T_RISE = 0.55       # 起身+起步
T_STOP = 0.65       # 减速停住


def body_state(t, total):
    """返回 (pos_xy, stand_u, head_yaw_extra, walk_phase)"""
    t_stop_start = total - T_STOP
    rise_start = T_REACT
    rise_end = rise_start + T_RISE
    walk_end = t_stop_start

    if t <= 0.0:
        return START.copy(), 0.0, 0.0, 0.0
    if rise_end >= walk_end:      # 极短时长保护
        walk_end = rise_end + 0.05
        t_stop_start = walk_end

    # 起身
    if t < rise_start:
        stand_u = 0.0
    elif t < rise_end:
        stand_u = smooth((t - rise_start) / max(rise_end - rise_start, 1e-6))
    else:
        stand_u = 1.0

    # 位移参数
    if t < rise_end:
        s = 0.06 * smooth(np.clip((t - rise_start) / max(rise_end - rise_start, 1e-6), 0, 1))
    elif t < walk_end:
        s = 0.06 + 0.86 * ease_walk((t - rise_end) / max(walk_end - rise_end, 1e-6))
    else:
        s = 0.92 + 0.08 * smooth(np.clip((t - walk_end) / max(T_STOP, 1e-6), 0, 1))

    s = float(np.clip(s, 0, 1))
    pos = START + (END - START) * s
    phase = (t - rise_end) * 6.0 if t > rise_end else 0.0
    return pos, stand_u, 0.0, phase


def smooth(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def ease_walk(u):
    """起步略慢、中段接近匀速、末段轻微收敛"""
    u = float(np.clip(u, 0, 1))
    return 0.15 * smooth(u * 3.0) + 0.85 * (1 - (1 - u) ** 1.25)


# ---- 相机：相对主体的「方位角 + 距离」跟随，末段绕到侧前方 ----
def camera_state(t, total, body_pos, heading):
    u = np.clip(t / max(total, 1e-6), 0, 1)
    # 弧移集中在后半程：前段保持侧后跟拍（藏脸），后段绕到侧前（揭示）
    arc = smooth(np.clip((u - 0.30) / 0.62, 0, 1))
    theta = math.radians(-142 + 104 * arc)          # 相对行进朝向的方位角
    dist = 3.05 - 0.95 * smooth(np.clip((u - 0.15) / 0.80, 0, 1))
    cz = 1.62 - 0.24 * arc
    focal = 34 + 10 * smooth(np.clip((u - 0.25) / 0.70, 0, 1))
    dx, dy = math.cos(math.radians(heading)), math.sin(math.radians(heading))
    ox = dx * math.cos(theta) - dy * math.sin(theta)
    oy = dx * math.sin(theta) + dy * math.cos(theta)
    cam = np.array([body_pos[0] + ox * dist, body_pos[1] + oy * dist, cz])
    # 注视点：主体胸口略偏向前方目标（引导视线）
    lead = 0.05 + 0.32 * arc
    tgt = np.array([body_pos[0] + dx * lead, body_pos[1] + dy * lead, 1.02 + 0.10 * arc])
    return cam, tgt, focal


def heading_of(pos, t, total):
    """朝向：起身时先转向声源，行走时朝路径方向"""
    dx, dy = (GHOST_POS[0] - pos[0]), (GHOST_POS[1] - pos[1])
    return math.degrees(math.atan2(dy, dx))


# ============================ 渲染 ============================
def render_scene(cam, tgt, focal, t, body_faces, label, hud=None):
    C = np.array(cam, dtype=float)
    T = np.array(tgt, dtype=float)
    fwd = T - C
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0]))
    right = right / np.linalg.norm(right)
    upv = np.cross(right, fwd)

    hfov = 2.0 * math.atan(18.0 / focal)
    fpx = (W / 2.0) / math.tan(hfov / 2.0)

    faces = list(SCENE_STATIC) + list(body_faces) + list(GHOST)
    img = Image.new("RGB", (W, H), (236, 236, 240))
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
        shade = 0.36 + 0.64 * max(0.0, float(np.dot(n, LIGHT)))
        items.append((sum(zs) / len(zs), [(int(round(a)), int(round(b))) for a, b in pts],
                      tuple(int(min(255, c * shade)) for c in color)))

    for _, pts, col in sorted(items, key=lambda x: -x[0]):
        ImageDraw.Draw(img).polygon(pts, fill=col, outline=(70, 70, 75))

    d = ImageDraw.Draw(img)
    if label:
        d.rectangle([0, 0, W, 58], fill=(250, 250, 252))
        d.text((14, 14), label, fill=(25, 25, 30), font=FONT(24))
    if hud:
        yy = H - 150
        d.rectangle([0, yy - 12, W, H], fill=(250, 250, 252))
        for i, line in enumerate(hud):
            d.text((16, yy + i * 32), line, fill=(30, 30, 36), font=FONT(22))
    return img


def FONT(size=24):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def frame_at(t, total):
    pos, stand_u, _, phase = body_state(t, total)
    head = heading_of(pos, t, total)
    # 起身后头部额外朝向：开场先看声源，行走到后半段回正对前方
    faces_local, _ = human_local(stand_u, phase)
    body = place_body(faces_local, pos[0], pos[1], head)
    cam, tgt, focal = camera_state(t, total, pos, head)
    return cam, tgt, focal, body, pos, stand_u


# ============================ 任务 ============================
def task_keys():
    for total in (4.0,):
        for tv in (0.0, total * 0.35, total * 0.62, total * 0.85, total):
            cam, tgt, focal, body, pos, su = frame_at(tv, total)
            moved = float(np.linalg.norm(pos - START))
            hud = ["行走 %.2f m / 全程 %.2f m" % (moved, TOTAL_DIST),
                   "剩余 %.2f m   焦距 %.0fmm" % (TOTAL_DIST - moved, focal),
                   "提示：😀=脸朝向（看得见脸才算数）"]
            img = render_scene(cam, tgt, focal, tv, body,
                               "t=%.2fs / %.1fs   行进 %.0f%%" % (tv, total, moved / TOTAL_DIST * 100),
                               hud)
            img.save(os.path.join(OUT, "keys_%s_t%04d.png" % (str(total).replace('.', ''), int(tv * 100))))
    print("KEYS OK")


def task_anim():
    import cv2
    for total in (4.0, 3.0):
        n = int(round(total * FPS))
        arr = []
        for i in range(n):
            t = i / FPS
            cam, tgt, focal, body, pos, su = frame_at(t, total)
            moved = float(np.linalg.norm(pos - START))
            hud = ["行进 %.2f / %.2f m  (%d%%)" % (moved, TOTAL_DIST, int(moved / TOTAL_DIST * 100)),
                   "焦距 %.0fmm" % focal]
            img = render_scene(cam, tgt, focal, t, body,
                               "%d 秒版 循声追踪  t=%.2fs" % (int(total) if total == 3.0 else 4, t), hud)
            arr.append(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
        tag = "track_%ds%s" % (int(total), globals().get("OUT_SFX", ""))
        p = os.path.join(OUT, tag + ".mp4")
        wr = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
        for f in arr:
            wr.write(f)
        wr.release()
        print("ANIM OK", p, len(arr), "frames")


def task_budget():
    print("全程距离：%.2f m（起身后站位 → 魅影前 0.7m 停住）" % TOTAL_DIST)
    for total in (3.0, 4.0, 5.0):
        moved_max = float(np.linalg.norm(body_state(total, total)[0] - START))
        # 估算步行峰值速度
        ts = np.linspace(0, total, 201)
        sp = []
        for i in range(1, len(ts)):
            dt = ts[i] - ts[i - 1]
            p0 = body_state(ts[i - 1], total)[0]
            p1 = body_state(ts[i], total)[0]
            sp.append(float(np.linalg.norm(p1 - p0)) / dt)
        print("  %.0f 秒：走 %.2f m（完成 %.0f%%）  峰值速度 %.2f m/s  平均 %.2f m/s"
              % (total, moved_max, moved_max / TOTAL_DIST * 100, max(sp), moved_max / total))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if "--short" in sys.argv:   # 3秒短距版：只逼近两步，走 1.0m 而非 2.2m
        END = np.array([-0.72, -0.62])
        TOTAL_DIST = float(np.linalg.norm(END - START))
        OUT_SFX = "_short"
    else:
        OUT_SFX = ""
    if mode in ("budget", "all"):
        task_budget()
    if mode in ("keys", "all"):
        task_keys()
    if mode in ("anim", "all"):
        task_anim()
