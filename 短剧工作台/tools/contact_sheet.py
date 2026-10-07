# -*- coding: utf-8 -*-
"""把 shot-diagrams 目录下的示意图拼成一张联排图，便于一眼检查一致性。"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

SRC = Path(r"D:/Aicomfyui/短剧工作台/assets-src/shot-diagrams")  # 看图看原图（清晰）
OUT = SRC.parent.parent.parent / "tools" / "contact_sheet.png"

names = sys.argv[1:] or sorted(p.stem for p in SRC.glob("*.png") if not p.stem.startswith("_"))
TW, TH = 180, 315
COLS = 5
rows = (len(names) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * (TW + 8) + 8, rows * (TH + 26) + 8), "white")
d = ImageDraw.Draw(sheet)
for i, n in enumerate(names):
    p = SRC / f"{n}.png"
    if not p.exists():
        continue
    im = Image.open(p).convert("RGB").resize((TW, TH), Image.LANCZOS)
    x = 8 + (i % COLS) * (TW + 8)
    y = 8 + (i // COLS) * (TH + 26)
    sheet.paste(im, (x, y))
    d.rectangle([x - 1, y - 1, x + TW, y + TH], outline=(200, 200, 200))
    d.text((x + 2, y + TH + 5), n, fill=(0, 0, 0))
sheet.save(OUT)
print(f"saved {OUT}  ({sheet.size[0]}x{sheet.size[1]})  items={len(names)}")
