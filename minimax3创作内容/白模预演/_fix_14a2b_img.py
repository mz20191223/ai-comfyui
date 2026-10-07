# -*- coding: utf-8 -*-
import io

p = r'D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_中文视频提示词_核对版.md'
s = io.open(p, encoding='utf-8').read()

def patch(sec_start, sec_end_marker, edits):
    """在 sec_start 到 sec_end_marker 之间做替换"""
    global s
    i = s.find(sec_start)
    j = s.find(sec_end_marker, i)
    assert i > 0 and j > i, sec_start
    seg = s[i:j]
    for old, new in edits:
        n = seg.count(old)
        assert n == 1, (sec_start[:20], old[:30], n)
        seg = seg.replace(old, new)
    s = s[:i] + seg + s[j:]
    print('patched:', sec_start[:26])

# ---------- 14a-2 ----------
patch(
    '## 镜头14a-2｜环绕过客',
    '## 镜头14b｜猛回头',
    [
        (
            'Image 4：权限魅影_角色参考图.jpg —— **仅取灰黑雾气的色调与半透明流动质感**（本镜魅影不显人形，只凝出一只雾手）',
            'Image 4：权限魅影_角色参考图.jpg —— **仅取灰黑雾气的色调与半透明流动质感**（本镜魅影不显人形，只凝出一只雾手）\n'
            'Image 5：公司办公室_场景参考图.jpg —— 仅作熄灯工位环境参考（工位排布、半高隔断、黑屏显示器、空转椅），严禁复制其拼贴排版、色块说明与色值标注'
        ),
        (
            '⑨ 无字幕、无水印、无其他人入画。\n\n**API参数：**\n- ref_image_0: 0114a1_tail.jpg',
            '⑨ **环境严格按 Image 5**：四周全是熄灯的工位与暗墙——严禁出现窗户、落地玻璃、城市夜景、天际线或任何室外光源，屏幕只发暗红微光、不显示任何内容；⑩ 无字幕、无水印、无其他人入画。\n\n**API参数：**\n- ref_image_0: 0114a1_tail.jpg'
        ),
        (
            '- ref_image_3: 权限魅影_角色参考图.jpg（仅雾气质感）\n- duration: 5',
            '- ref_image_3: 权限魅影_角色参考图.jpg（仅雾气质感）\n- ref_image_4: 公司办公室_场景参考图.jpg（熄灯工位环境参考）\n- duration: 5'
        ),
    ]
)

# ---------- 14b ----------
patch(
    '## 镜头14b｜猛回头',
    '## 镜头14c｜过客质问',
    [
        (
            'Image 4：权限魅影_角色参考图.jpg —— 魅影形态参考（**本镜开始凝出人形**：半透明灰黑雾态人形、身形修长、核心较实体化、边缘飘散、面部五官不清晰）',
            'Image 4：权限魅影_角色参考图.jpg —— 魅影形态参考（**本镜开始凝出人形**：半透明灰黑雾态人形、身形修长、核心较实体化、边缘飘散、面部五官不清晰）\n'
            'Image 5：公司办公室_场景参考图.jpg —— 仅作熄灯工位环境参考（工位排布、半高隔断、黑屏显示器、空转椅），严禁复制其拼贴排版、色块说明与色值标注'
        ),
        (
            '⑨ 无字幕、无水印、无其他人入画。\n\n**API参数：**\n- ref_image_0: 0114a2_tail.jpg',
            '⑨ **环境严格按 Image 5**：四周全是熄灯的工位与暗墙——严禁出现窗户、落地玻璃、城市夜景、天际线或任何室外光源，屏幕只发暗红微光、不显示任何内容；⑩ 无字幕、无水印、无其他人入画。\n\n**API参数：**\n- ref_image_0: 0114a2_tail.jpg'
        ),
        (
            '- ref_image_3: 权限魅影_角色参考图.jpg（魅影形态参考）\n- duration: 4',
            '- ref_image_3: 权限魅影_角色参考图.jpg（魅影形态参考）\n- ref_image_4: 公司办公室_场景参考图.jpg（熄灯工位环境参考）\n- duration: 4'
        ),
    ]
)

# ---------- 分镜图文档：14a-1 补"出图不传 vs 出视频要传"的说明 ----------
p2 = r'D:\Aicomfyui\minimax3创作内容\deepseek分镜\第1集_分镜图提示词_GPT-Img2.md'
t = io.open(p2, encoding='utf-8').read()
old = '> ⚠️ **本图不传权限魅影_角色参考图**：本图只需一团"不成形的雾"，传角色图会把人形带进来。'
new = ('> ⚠️ **本图不传权限魅影_角色参考图**：本图只需一团"不成形的雾"，传角色图会把人形带进来。\n'
       '> （注：这是**出图**时的取舍——**出视频**时 14a-1 会传魅影参考图作 Image 3，仅取灰黑雾气的色调与流动质感，因为视频里那团雾要持续存在 4 秒；出图只是一帧，不需要。）')
assert t.count(old) == 1
t = t.replace(old, new)
io.open(p2, 'w', encoding='utf-8').write(t)
print('patched: 分镜图 14a-1 注释')

io.open(p, 'w', encoding='utf-8').write(s)
print('视频文档写入完成，字符数:', len(s))
