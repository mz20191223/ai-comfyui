#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 0 · 文字 → 自动扩写提示词 → 文生图参考图（一键入口）

用户随便写一句（如「皮克斯质感小兔子」）：
  1) prompt_expand 自动扩成完整英文提示词
  2) 注入 t2i_ref.json（SDXL + Canopus Pixar LoRA 文生图工作流）
  3) 提交到 HAI ComfyUI，下载生成的参考图

用法:
  python gen_ref_image.py "皮克斯质感小兔子" --host http://43.155.214.240:6889
  python gen_ref_image.py "戴帽子的小猫 迪士尼风" --offline --host http://HOST:PORT
  python gen_ref_image.py "一只熊猫" --style pixar --seed 123 --out ref_out

说明:
  - 不加 --host 默认 http://43.155.214.240:6889（HAI 今早实例，已停则自行改地址）
  - 生成结果落在 --out 目录（默认 ref_out/），文件名 refimg_00001_.png
  - 若想"随机输入测不同角色"，多次换文字即可；同一文字+同 seed 可复现
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T2I_WF = os.path.join(HERE, "t2i_ref.json")
RUN_COMFY = os.path.join(HERE, "run_comfy.py")

# 把提示词注入工作流并落一个临时文件
def build_wf(pos, neg, width=832, height=1216, seed=None):
    with open(T2I_WF, encoding="utf-8") as f:
        wf = json.load(f)
    wf["6"]["inputs"]["text"] = pos
    wf["7"]["inputs"]["text"] = neg
    wf["5"]["inputs"]["width"] = width
    wf["5"]["inputs"]["height"] = height
    if seed is not None:
        wf["3"]["inputs"]["seed"] = seed
    tmp = os.path.join(HERE, "t2i_ref._generated.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    return tmp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="用户简短描述，如『皮克斯质感小兔子』")
    ap.add_argument("--host", default=os.environ.get("COMFY_HOST", "http://43.155.214.240:6889"))
    ap.add_argument("--style", help="强制风格 pixar/disney/realistic/anime/clay/blindbox")
    ap.add_argument("--offline", action="store_true", help="不用 LLM，模板扩写")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "ref_out"))
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--height", type=int, default=1216)
    a = ap.parse_args()

    # 1) 扩写
    sys.path.insert(0, HERE)
    from prompt_expand import expand
    print("==> 扩写提示词中 ...")
    obj = expand(a.text, style=a.style, offline=a.offline)
    print("    风格:", obj.get("style"), "| 主体:", obj.get("subject_en"))
    print("    正向:", obj["positive"][:120], "...")

    # 2) 注入并生成临时工作流
    tmp = build_wf(obj["positive"], obj["negative"], a.width, a.height, a.seed)

    # 3) 提交到 ComfyUI
    print("==> 提交到 ComfyUI:", a.host)
    cmd = [sys.executable, RUN_COMFY, tmp, "--host", a.host, "--out", a.out]
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        print("!! 生成失败，检查 HAI 是否在线 / 地址是否正确")
        sys.exit(rc)
    # 顺带把扩写结果也存一份，方便后续复用
    with open(os.path.join(a.out, "prompt_expand.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print("✅ 参考图已生成在", a.out, "（含 prompt_expand.json 记录本次扩写）")


if __name__ == "__main__":
    main()
