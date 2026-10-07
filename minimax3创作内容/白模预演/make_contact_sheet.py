"""
把 out_py 里的机位图拼成一张 9 宫格总览，便于一次性比对机位。
运行：C:\\Python313\\python.exe make_contact_sheet.py
"""
import os
from PIL import Image, ImageDraw, ImageFont

SRC = r"D:\Aicomfyui\minimax3创作内容\白模预演\out_py"
OUT = r"D:\Aicomfyui\minimax3创作内容\白模预演\机位总览_9宫格.png"

CELL_W, CELL_H = 360, 640
LABEL_H = 46
PAD = 10
BG = (250, 250, 252)

SHOTS = [
    ("01_wide_3q.png", "01 3/4前侧全景 35mm"),
    ("02_side_mid.png", "02 侧面中景 50mm"),
    ("03_front_50mm.png", "03 镜头=屏幕位 50mm"),
    ("04_front_85mm.png", "04 镜头=屏幕位 85mm（13d候选）"),
    ("05_screen_13c.png", "05 屏幕微俯特写（13c候选）"),
    ("06_over_shoulder.png", "06 右后越肩看屏"),
    ("07_keyboard_top.png", "07 键盘右后俯拍（6c候选）"),
    ("08_pov_screen.png", "08 过客主观看屏 35mm"),
    ("09_top_layout.png", "09 顶部布局俯视"),
]


def load_font(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    cols, rows = 3, 3
    W = cols * CELL_W + (cols + 1) * PAD
    H = rows * (CELL_H + LABEL_H) + (rows + 1) * PAD
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    font = load_font(22)

    for i, (fn, label) in enumerate(SHOTS):
        path = os.path.join(SRC, fn)
        if not os.path.exists(path):
            continue
        im = Image.open(path).convert("RGB")
        tw, th = CELL_W, CELL_H
        sw, sh = im.size
        scale = min(tw / sw, th / sh)
        nw, nh = int(sw * scale), int(sh * scale)
        im = im.resize((nw, nh), Image.LANCZOS)
        cell = Image.new("RGB", (tw, th), (255, 255, 255))
        cell.paste(im, ((tw - nw) // 2, (th - nh) // 2))

        c = i % cols
        r = i // cols
        x = PAD + c * (CELL_W + PAD)
        y = PAD + r * (CELL_H + LABEL_H + PAD)
        canvas.paste(cell, (x, y))
        d.rectangle([x, y, x + tw, y + th], outline=(150, 150, 160), width=1)
        d.text((x + 4, y + th + 12), label, fill=(30, 30, 35), font=font)

    canvas.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
