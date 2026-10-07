"""
过客工位白模（blockout）+ 多机位渲染
用途：给《凌晨两点，Bug成精了》做机位/构图验证（previz），不用于最终出片。
坐标：地面 z=0，过客坐于原点附近、面朝 +Y，屏幕在 +Y 侧。
单位：米。
"""
import bpy
import os

OUT = r"D:\Aicomfyui\minimax3创作内容\白模预演\out"
os.makedirs(OUT, exist_ok=True)

# ---------- 引擎选择（兼容 Blender 各版本命名） ----------
items = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
print("ENGINES:", items)
for pref in ['BLENDER_WORKBENCH', 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES']:
    if pref in items:
        ENGINE = pref
        break
print("USE ENGINE:", ENGINE)

# ---------- 清场 ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

sc = bpy.context.scene
sc.render.engine = ENGINE
sc.render.resolution_x = 720
sc.render.resolution_y = 1280
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'
sc.render.image_settings.color_depth = '8'
sc.render.image_settings.compression = 15
sc.render.film_transparent = False
if ENGINE == 'CYCLES':
    sc.cycles.samples = 32


def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)  # Workbench / 视口显示色
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs[0].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
    return m


M_FLOOR = mat('m_floor', (0.88, 0.88, 0.88))
M_DESK = mat('m_desk', (0.68, 0.66, 0.63))
M_BODY = mat('m_body', (0.96, 0.94, 0.91))     # 过客：最亮，视觉主角
M_SCREEN = mat('m_screen', (0.13, 0.13, 0.15))  # 屏幕：深色
M_METAL = mat('m_metal', (0.52, 0.52, 0.55))
M_KB = mat('m_kb', (0.92, 0.92, 0.92))


def box(name, size, loc, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    o.data.materials.append(material)
    return o


def sph(name, r, loc, material):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return o


def cyl(name, r, h, loc, material):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return o


# ---------- 地面 ----------
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
bpy.context.object.name = 'floor'
bpy.context.object.data.materials.append(M_FLOOR)

# ---------- 桌子（桌面上表面 z=0.75，深 0.75，宽 1.6） ----------
box('desktop', (1.60, 0.75, 0.04), (0, 0.375, 0.73), M_DESK)
box('leg_L', (0.04, 0.70, 0.73), (-0.78, 0.375, 0.365), M_METAL)
box('leg_R', (0.04, 0.70, 0.73), (0.78, 0.375, 0.365), M_METAL)

# ---------- 显示器（屏幕朝 -Y，正对过客） ----------
box('screen_base', (0.24, 0.18, 0.02), (0, 0.65, 0.76), M_METAL)
box('screen_pillar', (0.05, 0.05, 0.28), (0, 0.65, 0.90), M_METAL)
box('screen_panel', (0.62, 0.03, 0.37), (0, 0.685, 1.10), M_SCREEN)

# ---------- 键鼠 ----------
box('keyboard', (0.44, 0.15, 0.02), (0, 0.25, 0.76), M_KB)
box('mouse', (0.06, 0.10, 0.03), (0.35, 0.25, 0.775), M_KB)

# ---------- 椅子 ----------
box('chair_seat', (0.50, 0.50, 0.06), (0, -0.35, 0.45), M_METAL)
box('chair_back', (0.48, 0.06, 0.55), (0, -0.60, 0.72), M_METAL)
cyl('chair_post', 0.04, 0.42, (0, -0.35, 0.21), M_METAL)
box('chair_foot', (0.60, 0.60, 0.04), (0, -0.35, 0.02), M_METAL)

# ---------- 过客（坐姿白模，面朝 +Y） ----------
box('torso', (0.44, 0.26, 0.62), (0, -0.18, 0.76), M_BODY)      # 躯干 z 0.45→1.07
cyl('neck', 0.05, 0.10, (0, -0.15, 1.10), M_BODY)
sph('head', 0.115, (0, -0.15, 1.20), M_BODY)                     # 眼高约 1.20
box('thigh_L', (0.16, 0.45, 0.14), (-0.12, 0.10, 0.55), M_BODY)
box('thigh_R', (0.16, 0.45, 0.14), (0.12, 0.10, 0.55), M_BODY)
box('shin_L', (0.14, 0.14, 0.45), (-0.12, 0.32, 0.25), M_BODY)
box('shin_R', (0.14, 0.14, 0.45), (0.12, 0.32, 0.25), M_BODY)
box('foot_L', (0.12, 0.25, 0.06), (-0.12, 0.42, 0.03), M_BODY)
box('foot_R', (0.12, 0.25, 0.06), (0.12, 0.42, 0.03), M_BODY)
box('upperarm_L', (0.11, 0.11, 0.30), (-0.25, -0.14, 0.92), M_BODY)
box('upperarm_R', (0.11, 0.11, 0.30), (0.25, -0.14, 0.92), M_BODY)
box('forearm_L', (0.10, 0.34, 0.10), (-0.22, 0.05, 0.79), M_BODY)
box('forearm_R', (0.10, 0.34, 0.10), (0.22, 0.05, 0.79), M_BODY)
box('hand_L', (0.10, 0.12, 0.06), (-0.20, 0.23, 0.79), M_BODY)
box('hand_R', (0.10, 0.12, 0.06), (0.20, 0.23, 0.79), M_BODY)

# ---------- 灯光（Workbench 会忽略，EEVEE/CYCLES 需要） ----------
bpy.ops.object.light_add(type='SUN', location=(2.0, -2.0, 3.0))
sun = bpy.context.object
sun.data.energy = 4.0
sun.rotation_euler = (0.7, 0.0, 0.9)


def add_shot(name, cam_loc, target, lens):
    """建一个 look-at 目标空物体 + 带 TrackTo 约束的相机"""
    bpy.ops.object.empty_add(location=target)
    tgt = bpy.context.object
    tgt.name = 'tgt_' + name
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.object
    cam.name = 'cam_' + name
    cam.data.lens = lens
    c = cam.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return cam


# ---------- 机位表：(文件名, 相机位置, 注视点, 焦距mm) ----------
SHOTS = [
    ('01_全景_空间关系', (1.80, -1.40, 1.55), (0, 0.20, 0.85), 35),
    ('02_侧面中景', (1.70, 0.35, 1.30), (0, 0.15, 0.95), 50),
    ('03_正面_镜头在屏幕位_50mm', (0.00, 0.55, 1.25), (0, -0.15, 1.20), 50),
    ('04_正面_镜头在屏幕位_85mm', (0.00, 0.55, 1.25), (0, -0.15, 1.20), 85),
    ('05_屏幕特写_13c', (0.42, -0.02, 1.32), (0, 0.685, 1.08), 35),
    ('06_越肩_关弹窗', (0.55, -0.75, 1.42), (0, 0.60, 1.05), 40),
    ('07_键盘俯拍_右后45', (0.85, -0.25, 1.30), (0, 0.22, 0.77), 50),
    ('08_主观视角_看屏幕', (0.00, -0.15, 1.20), (0, 0.685, 1.10), 35),
]

rendered = []
for name, loc, tgt, lens in SHOTS:
    cam = add_shot(name, loc, tgt, lens)
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, name + '.png')
    bpy.ops.render.render(write_still=True)
    rendered.append(name + '.png')
    print("RENDERED:", name, flush=True)

# ---------- 保存场景，便于后续复用/改机位 ----------
blend_path = r"D:\Aicomfyui\minimax3创作内容\白模预演\workstation.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

print("ALL DONE ->", OUT)
print("FILES:", rendered)
