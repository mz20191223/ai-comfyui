"""make_montage.py — 把 grid/ 下 25 张分镜拼成带格号标签的 5x5 总览图。

用法: python make_montage.py [--grid grid] [--out grid_montage_labeled.png] [--cell 320]
依赖 Pillow。
"""
import argparse, json, os
from PIL import Image, ImageDraw, ImageFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", default="grid")
    ap.add_argument("--json", default="storyboard_25grid.json")
    ap.add_argument("--out", default="grid_montage_labeled.png")
    ap.add_argument("--cell", type=int, default=320)
    a = ap.parse_args()

    cfg = json.load(open(a.json, encoding="utf-8"))
    rows, cols = cfg["rows"], cfg["cols"]
    cell = a.cell
    label_h = 34
    W = len(cols) * cell
    H = len(rows) * (cell + label_h)
    canvas = Image.new("RGB", (W, H), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for ri, r in enumerate(rows):
        for ci, c in enumerate(cols):
            p = f"{a.grid}/{r['key']}_{c['key']}.png"
            if not os.path.exists(p):
                print("缺失:", p); continue
            im = Image.open(p).convert("RGB").resize((cell, cell))
            x = ci * cell
            y = ri * (cell + label_h)
            canvas.paste(im, (x, y))
            draw.rectangle([x, y + cell, x + cell, y + cell + label_h],
                           fill=(220, 220, 220))
            draw.text((x + 6, y + cell + 8), f"{r['key']}_{c['key']}",
                      fill=(20, 20, 20), font=font)
    canvas.save(a.out)
    print(f"DONE {a.out} {canvas.size}")


if __name__ == "__main__":
    main()
