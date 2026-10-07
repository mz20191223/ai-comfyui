#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_storyboard.py —— 用免费 Agnes 出「25 宫格分镜视觉板」并拼成 5x5 大图。

用途：规划分镜（场景/构图/镜头类型）并驱动后续视频。默认图生图(传 hero 参考)，
25 格与原始刺猬(hedgehog_hero.png)保持一致；纯文生图(无 --ref)时 25 格不一致。
角色最终一致性由 Phantom 吃参考图集(hero+25格相关格)在出片时二次锚定保证。

流程：
  1. 读 storyboard_25grid.json（5 行场景 × 5 列镜头类型 = 25 格）
  2. 每格调 Agnes 文生图 → storyboard/cell_<r><c>.png
  3. PIL 拼成 5x5 的 storyboard_25grid.png

依赖：agnes_image.py（同目录）；Pillow（自动装在 managed venv）。
用法：
  python gen_storyboard.py
  python gen_storyboard.py --plan storyboard_25grid.json --out storyboard_25grid.png --cols 5
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from agnes_image import generate_image, download_image  # noqa: E402


def ensure_pillow():
    """确保 managed venv 有 Pillow；没有就装。"""
    venv_py = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
    if not os.path.exists(venv_py):
        venv_py = sys.executable
    try:
        import PIL  # noqa
        return venv_py
    except Exception:
        pass
    try:
        subprocess.run([venv_py, "-m", "pip", "install", "Pillow", "-q"], check=True)
    except Exception as e:
        print("⚠️ 安装 Pillow 失败:", e, "将跳过拼板，仅保存单格图")
        return None
    return venv_py


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=os.path.join(HERE, "storyboard_25grid.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "storyboard_25grid.png"))
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--ref", default=os.path.join(HERE, "hedgehog_hero.png"),
                    help="图生图角色锚点；传入则 25 格与原始刺猬一致，缺省=hedgehog_hero.png")
    a = ap.parse_args()

    with open(a.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)
    prefix = plan.get("style_prefix", "")
    rows = plan["rows"]
    cols = plan["cols"]
    ncols = a.cols

    out_dir = os.path.join(HERE, "storyboard")
    os.makedirs(out_dir, exist_ok=True)

    cells = {}
    warned_no_ref = False
    ref_mode = "图生图(hero锚定)" if (a.ref and os.path.exists(a.ref)) else "纯文生图(不一致)"
    print(f"==> 生成 {len(rows)}×{len(cols)} = {len(rows)*len(cols)} 张分镜图 (Agnes 免费, {ref_mode}) ...")
    for ri, row in enumerate(rows):
        for ci, col in enumerate(cols):
            tag = f"{row['key']}{col['key']}"
            prompt = f"{prefix}。{row['scene']}，{col['shot']}"
            cell_path = os.path.join(out_dir, f"cell_{tag}.png")
            cells[(ri, ci)] = cell_path
            if os.path.exists(cell_path):
                print(f"  [{tag}] 已存在，跳过")
                continue
            print(f"  [{tag}] {prompt[:40]} ...")
            try:
                if a.ref and os.path.exists(a.ref):
                    r = generate_image(prompt, size=a.size, image=a.ref)
                else:
                    if not warned_no_ref:
                        print(f"  ⚠️ 参考图 {a.ref} 不存在，退化为纯文生图（25格将不一致）")
                        warned_no_ref = True
                    r = generate_image(prompt, size=a.size)
                if r.get("url"):
                    download_image(r["url"], cell_path)
                elif r.get("b64_json"):
                    download_image(r["b64_json"], cell_path)
                else:
                    print(f"    ⚠️ 无返回: {r}")
            except Exception as e:
                print(f"    ⚠️ 调用失败: {e}")

    # 拼板
    venv_py = ensure_pillow()
    if not venv_py:
        print("✅ 单格图已存于 storyboard/（缺 Pillow，未拼大图）")
        return

    # 用 managed venv 的 python 跑拼板，确保 PIL 可用
    montage = os.path.join(HERE, "_montage.py")
    with open(montage, "w", encoding="utf-8") as f:
        f.write(_MONTAGE_CODE)
    env = dict(os.environ)
    # 让 _montage.py 找到 cells 与输出
    cmd = [venv_py, montage, a.out, str(ncols)] + [
        f"{ri},{ci},{cells[(ri,ci)]}" for ri in range(len(rows)) for ci in range(len(cols))
    ]
    rc = subprocess.run(cmd, env=env)
    try:
        os.remove(montage)
    except OSError:
        pass
    if rc.returncode == 0 and os.path.exists(a.out):
        print(f"\n✅ 25 宫格分镜板: {a.out}")
    else:
        print(f"\n⚠️ 拼板失败，单格图在 storyboard/")


_MONTAGE_CODE = r'''
import sys
from PIL import Image
out = sys.argv[1]
ncols = int(sys.argv[2])
specs = [s.split(",", 2) for s in sys.argv[3:]]
imgs = {}
for ri, ci, path in specs:
    try:
        imgs[(int(ri), int(ci))] = Image.open(path).convert("RGB")
    except Exception:
        imgs[(int(ri), int(ci))] = None
rows = sorted({r for r, _ in imgs})
cols = sorted({c for _, c in imgs})
max_w = max((im.width for im in imgs.values() if im), default=512)
max_h = max((im.height for im in imgs.values() if im), default=512)
pad = 8
W = ncols * max_w + (ncols + 1) * pad
H = len(rows) * max_h + (len(rows) + 1) * pad
canvas = Image.new("RGB", (W, H), (20, 20, 20))
for (ri, ci), im in imgs.items():
    x = pad + ci * (max_w + pad)
    y = pad + ri * (max_h + pad)
    if im:
        canvas.paste(im, (x, y))
canvas.save(out)
'''


if __name__ == "__main__":
    main()
