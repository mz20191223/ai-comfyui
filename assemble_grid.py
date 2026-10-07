"""把 9 张生成的刺猬图拼成 3x3 角色设定表（带格子标签）。
用法：
  1) 在 ComfyUI 用 hedgehog_9grid_ipadapter_workflow.json 跑 9 次，分别用 9 张姿势骨架，
     导出 9 张 PNG 到本地某文件夹（建议按 01_..09_ 命名）。
  2) 修改下面 IN_DIR / OUT 路径，运行：
     python assemble_grid.py
"""
from PIL import Image, ImageDraw, ImageFont
import os, glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IN_DIR = os.path.join(SCRIPT_DIR, "hedgehog_9grid_out")
OUT = os.path.join(SCRIPT_DIR, "hedgehog_9grid_final.png")

# 9 宫格顺序（行优先）：角度行 / 角度行 / 表情行
ORDER = [
    "01_front_neutral.png", "02_3q_left.png",     "03_3q_right.png",
    "04_side_left.png",     "05_side_right.png",  "06_back.png",
    "07_happy_arms_up.png", "08_surprised_hands_face.png", "09_wink_hand_hip.png",
]
LABELS = [
    "正面·平静", "3/4左", "3/4右",
    "左侧面", "右侧面", "背面",
    "开心·举手", "惊讶·捂脸", "俏皮·眨眼",
]

CELL = 512          # 每格宽度
GAP = 24            # 格子间距
PAD = 60            # 外边距（放标题）
COLS, ROWS = 3, 3

def find_file(name):
    p = os.path.join(IN_DIR, name)
    if os.path.exists(p):
        return p
    # 容错：按前缀匹配
    cand = glob.glob(os.path.join(IN_DIR, name.split("_")[0] + "*.png"))
    return cand[0] if cand else None

def main():
    imgs = []
    for name in ORDER:
        f = find_file(name)
        if not f:
            raise SystemExit(f"缺少图片：{name}（在 {IN_DIR} 中）")
        im = Image.open(f).convert("RGB")
        im = im.resize((CELL, int(CELL * 1152 / 1024)))  # 统一比例
        imgs.append(im)

    cw = CELL
    ch = int(CELL * 1152 / 1024)
    W = PAD * 2 + COLS * cw + (COLS - 1) * GAP
    H = PAD * 2 + ROWS * ch + (ROWS - 1) * GAP + 40  # +40 标题行

    canvas = Image.new("RGB", (W, H), (245, 245, 248))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    except Exception:
        font = ImageFont.load_default()

    d.text((PAD, 16), "皮克斯刺猬 · 角色一致性设定表 (9-Grid)", fill=(30, 30, 40), font=font)

    for i, im in enumerate(imgs):
        r, c = divmod(i, COLS)
        x = PAD + c * (cw + GAP)
        y = PAD + 40 + r * (ch + GAP)
        canvas.paste(im, (x, y))
        d.rectangle([x, y, x + cw, y + ch], outline=(200, 200, 210), width=2)
        d.text((x + 10, y + 10), LABELS[i], fill=(20, 20, 30), font=font)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    canvas.save(OUT)
    print("已生成 9 宫格 ->", OUT, f"({W}x{H})")

if __name__ == "__main__":
    main()
