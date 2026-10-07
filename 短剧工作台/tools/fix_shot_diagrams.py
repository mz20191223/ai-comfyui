# -*- coding: utf-8 -*-
"""景别图：全身底图 + 白色留白 + 精确裁切（修掉裁到画外产生黑边的问题）。
视角图：只重试 POV。"""
import json
import os
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

API_KEY = os.environ.get("AGNES_API_KEY", """")
URL = "https://apihub.agnes-ai.com/v1/images/generations"
OUT = Path(r"D:/Aicomfyui/短剧工作台/assets-src/shot-diagrams")  # 原图放这儿，不进发布目录
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
CHARS = ("只画一个人物：一位日式动漫风格的青年男性角色，黑色短发、额前有碎发、"
         "五官清秀、穿纯白色圆领短袖T恤和深色长裤和浅色运动鞋。")


def gen(prompt, out: Path, size="1024x1792", retries=3) -> bool:
    payload = {"model": "agnes-image-2.1-flash", "prompt": prompt, "size": size, "n": 1}
    for a in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                URL, data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {API_KEY}",
                         "Content-Type": "application/json; charset=UTF-8"}, method="POST")
            with OPENER.open(req, timeout=180) as r:
                url = json.loads(r.read().decode("utf-8"))["data"][0]["url"]
            with OPENER.open(url, timeout=180) as r:
                data = r.read()
            out.write_bytes(data)
            print(f"  [OK] {out.name} {len(data)/1024:.0f} KB", flush=True)
            return True
        except Exception as e:
            print(f"  [retry {a}] {out.name}: {type(e).__name__}: {e}", flush=True)
            time.sleep(3 * a)
    print(f"  [FAIL] {out.name}", flush=True)
    return False


def bbox_of(img):
    a = np.asarray(img.convert("L"))
    m = a < 235
    rows = np.where(m.any(axis=1))[0]
    cols = np.where(m.any(axis=0))[0]
    if not len(rows) or not len(cols):
        raise RuntimeError("空白图")
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def make_crop(src, bb, fill, anchor="head", out_size=(720, 1280), pad_bg="white"):
    """fill = 画面高 / 人物身高。fill<1 表示裁进（紧景别），>1 表示留边（宽景别）。
    anchor='head' 让头顶贴画幅上沿；'center' 让人物垂直居中。"""
    x0, y0, x1, y1 = bb
    B = y1 - y0
    cx = (x0 + x1) / 2
    ch = fill * B
    cw = ch * 9 / 16
    if cw > src.width:          # 画幅宽度不够 → 收窄到满宽，等比反推高度
        cw = src.width
        ch = cw * 16 / 9
    cy = (y0 + ch / 2) if anchor == "head" else (y0 + B / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    canvas = Image.new("RGB", src.size, pad_bg)
    canvas.paste(src, (0, 0))
    crop = canvas.crop(tuple(int(round(v)) for v in box))
    return crop.resize(out_size, Image.LANCZOS)


SIZES = [
    ("size_ECU", 0.115, "head"),   # 大特写：眉眼
    ("size_CU",  0.267, "head"),   # 特写：头+肩
    ("size_MCU", 0.330, "head"),   # 中近景：胸以上
    ("size_MS",  0.430, "head"),   # 中景：腰以上
    ("size_MLS", 0.760, "head"),   # 中全景：膝以上
    ("size_LS",  1.180, "center"), # 全景：全身+上下留白
]


def main():
    # ---- 1) 白色留白扩容，给宽景别留出裁切余量 ----
    src0 = Image.open(OUT / "_ref_full.png").convert("RGB")
    pad_w, pad_h = int(src0.width * 1.45), int(src0.height * 1.45)
    src = Image.new("RGB", (pad_w, pad_h), "white")
    src.paste(src0, ((pad_w - src0.width) // 2, (pad_h - src0.height) // 2))
    bb = bbox_of(src)
    print(f"[1] 源 {src0.size} → 留白后 {src.size}, 人物包围盒 {bb}, 身高 {bb[3]-bb[1]}px")

    print("[2] 裁切景别 ...")
    for name, fill, anchor in SIZES:
        try:
            make_crop(src, bb, fill, anchor).save(OUT / f"{name}.png")
            print(f"  [OK] {name}  (fill={fill})")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    # ---- 2) 极远景：把全景图缩小到 22% 贴白底居中 ----
    try:
        ls = Image.open(OUT / "size_LS.png").convert("RGB")
        canvas = Image.new("RGB", (720, 1280), "white")
        s = ls.resize((int(720 * 0.22), int(1280 * 0.22)), Image.LANCZOS)
        canvas.paste(s, ((720 - s.width) // 2, (1280 - s.height) // 2))
        canvas.save(OUT / "size_ELS.png")
        print("  [OK] size_ELS")
    except Exception as e:
        print(f"  [FAIL] size_ELS: {e}")

    # ---- 3) POV 再试一次：极端强调「画面里没有人」 ----
    print("[3] 重试 POV ...")
    gen(
        "一张示意「第一人称主观视角」的黑白漫画线稿图。画面里只有一双从画幅下边缘伸入的双手，"
        "两只手掌张开、掌心朝向观者，手臂从画面左右两侧的下方伸进来。"
        "注意：画面中绝对不能出现任何人的脸、头、头发、脖子、躯干、衣服和腿。"
        "除了这双手和手臂以外，画面其余部分全部是纯白色空白。"
        "只用干净利落的黑色单线勾勒轮廓，不做阴影和网点。"
        "不要出现任何文字、汉字、字母、数字、符号、标注、箭头、参考线、边框、水印。"
        "整体为严格的竖向 9:16 竖构图。",
        OUT / "angle_POV.png")

    print("\n完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
