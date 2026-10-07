#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桃子「角色圣经」一键验证脚本（在 DSW 网页终端运行）
-------------------------------------------------
前置：DSW 实例已启动且 ComfyUI 在 127.0.0.1:6889 运行
      （在 DSW 网页打开 ComfyUI 一次即可，本脚本走本地环回，绕过网关登录）

用法：
  1) 打开 DSW 网页终端（PAI 控制台 -> 实例 -> 打开 -> Terminal）
  2) 把本文件内容保存为 gen_bible.py：
        cat > gen_bible.py <<'PY'
        ... (粘贴本文件全部内容) ...
        PY
  3) 运行： python3 gen_bible.py
  4) 等待 5 张（front / 3q_left / side / back / happy）依次生成

原理：Qwen-Image-Edit 正确用法 = 给桃子参考图 -> 同角色多角度/表情
      单 KSampler 串行（避免 A10 24G 多卡并行 OOM），denoise=0.6 保身份兼换角度
"""

import urllib.request
import json
import time

COMFY = "http://127.0.0.1:6889"

UNET = "qwen-image-edit-2511-Q4_K_M.gguf"
CLIP = "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
VAE  = "qwen_image_vae.safetensors"
REF  = "peach_role_v6.png"

NEG = ("low quality, blurry, out of focus, soft focus, deformed, extra limbs, "
       "bad anatomy, watermark, text, signature, jpeg artifacts, compression "
       "artifacts, noisy, grainy, pixelated, extra faces")

# (filename_prefix, 提示词) —— 全部以「SAME character from the reference」锚定身份
VIEWS = [
    ("bible_front",
     "Front view full-body of the SAME cute 3D chibi Pixar character from the reference image: "
     "the same round chubby peach body, big sparkling eyes, pink blush cheeks, tiny leaf on top, "
     "soft warm lighting and clean light-gray background. Facing camera, standing, both hands at sides. "
     "Keep the exact same art style, material and rendering quality as the original. "
     "8k uhd, masterpiece, best quality, sharp focus, highly detailed 3D render, crisp clean edges."),
    ("bible_3q_left",
     "Three-quarter view from the LEFT of the SAME cute 3D chibi Pixar character from the reference image: "
     "same round chubby peach body, big sparkling eyes, pink blush cheeks, tiny leaf, soft warm lighting, "
     "clean light-gray background. Head turned slightly to the left, showing the left side of the face. "
     "Keep the exact same art style and rendering. "
     "8k uhd, masterpiece, best quality, sharp focus, highly detailed 3D render."),
    ("bible_side",
     "Side profile view of the SAME cute 3D chibi Pixar character from the reference image: "
     "same round chubby peach body, big sparkling eyes in profile, pink blush cheek, tiny leaf on top, "
     "soft warm lighting and clean light-gray background. Facing left, full-body side view. "
     "Keep the exact same art style, material and rendering quality as the original. "
     "8k uhd, masterpiece, best quality, sharp focus, highly detailed 3D render."),
    ("bible_back",
     "Back view of the SAME cute 3D chibi Pixar character from the reference image: "
     "same round chubby peach body, tiny leaf on top, soft warm lighting, clean light-gray background. "
     "Seen from behind, showing the round back, the stubby legs and the little hands. "
     "Keep the exact same art style and rendering. "
     "8k uhd, masterpiece, best quality, sharp focus, highly detailed 3D render."),
    ("bible_happy",
     "Front view of the SAME cute 3D chibi Pixar character from the reference image with a BIG HAPPY expression: "
     "same round chubby peach body, big sparkling eyes, wide smile, pink blush cheeks, tiny leaf, "
     "soft warm lighting, clean light-gray background. Facing camera, laughing joyfully, both hands raised up. "
     "Keep the exact same art style and rendering. "
     "8k uhd, masterpiece, best quality, sharp focus, highly detailed 3D render."),
]


def build(prompt, prefix, seed):
    return {
        "1":  {"class_type": "UnetLoaderGGUF",        "inputs": {"unet_name": UNET}},
        "2":  {"class_type": "CLIPLoaderGGUF",        "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3":  {"class_type": "VAELoader",             "inputs": {"vae_name": VAE}},
        "4":  {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 1.73}},
        "7":  {"class_type": "LoadImage",             "inputs": {"image": REF}},
        "5":  {"class_type": "TextEncodeQwenImageEditPlus",
               "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["7", 0], "text": prompt}},
        "6":  {"class_type": "CLIPTextEncode",        "inputs": {"clip": ["2", 0], "text": NEG}},
        "8":  {"class_type": "VAEEncode",             "inputs": {"pixels": ["7", 0], "vae": ["3", 0]}},
        "9":  {"class_type": "KSampler", "inputs": {
                   "model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
                   "latent_image": ["8", 0],
                   "seed": seed, "steps": 35, "cfg": 7.5,
                   "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 0.6}},
        "10": {"class_type": "VAEDecode",             "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
        "11": {"class_type": "SaveImage",             "inputs": {"images": ["10", 0], "filename_prefix": prefix}},
    }


def post(wf):
    req = urllib.request.Request(
        COMFY + "/prompt",
        data=json.dumps({"prompt": wf}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["prompt_id"]


def wait(pid):
    for _ in range(240):  # 最多等 20 分钟
        try:
            with urllib.request.urlopen(COMFY + "/history/" + pid, timeout=10) as r:
                data = json.loads(r.read())
            if pid in data:
                return data[pid]
        except Exception:
            pass
        time.sleep(5)
    raise TimeoutError("等待超时：" + pid)


def main():
    print("=== 桃子角色圣经生成（Qwen-Image-Edit 同角色多角度/表情）===")
    for i, (prefix, prompt) in enumerate(VIEWS):
        seed = 1000 + i * 7
        wf = build(prompt, prefix, seed)
        try:
            pid = post(wf)
        except urllib.error.URLError as e:
            print("无法连接 ComfyUI(127.0.0.1:6889)：", e)
            print("请先在 DSW 网页打开 ComfyUI，让它运行在 6889 端口，再重跑本脚本。")
            return
        print(f"[{i+1}/{len(VIEWS)}] queued {prefix}  (prompt_id={pid})")
        res = wait(pid)
        outs = res.get("outputs", {}).get("11", {}).get("images", [])
        for im in outs:
            print("    ->", im.get("filename"), "| subfolder:", im.get("subfolder"))
        time.sleep(2)
    print("DONE：角色圣经 5 张已生成（front / 3q_left / side / back / happy）。")


if __name__ == "__main__":
    main()
