#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 PAI-DSW (A10) 本地 ComfyUI 出桃子多角度参考图。
与 HAI 版 gen_refs.py 节点图完全一致（已在 HAI 0.28.0 验证 test 通过、full 可提交），
仅把目标改成本机 ComfyUI (127.0.0.1:6889)。

链路: UnetLoaderGGUF(Qwen-Edit Q4) + ModelSamplingAuraFlow
      + CLIPLoaderGGUF(Qwen2.5-VL Q4, type=qwen_image)
      + CLIPTextEncode + QwenImageSampler + VAEDecode + SaveImage
用法（在 DSW Terminal，pai 目录下）:
  python gen_refs_pai.py test    # 单张 txt2img 验证链路（小图快，约 1~2 分钟）
  python gen_refs_pai.py full    # 4 张 img2img 多角度（以 anchor 初始化，保角色一致）
输出图片下载到 ./out/
"""
import subprocess, json, os, sys, time, uuid

# 本地 DSW 实例
COMFY_IP = os.environ.get("COMFY_HOST", "127.0.0.1")
HOST = f"http://{COMFY_IP}:6889"
CLIENT = uuid.uuid4().hex
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUTDIR, exist_ok=True)

UNET = "qwen-image-edit-2511-Q4_K_M.gguf"
CLIP = "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
VAE = "qwen_image_vae.safetensors"
ANCHOR = "peach_role_v6.png"
NEG = "low quality, blurry, deformed, extra limbs, bad anatomy, watermark, text, different character, color changed"


def api(path, data=None, binary=False, timeout=180):
    # 本地访问不需要代理；--noproxy 对 127.0.0.1 也无害
    cmd = ["curl", "-s", "--noproxy", COMFY_IP, "--max-time", str(timeout), f"{HOST}{path}"]
    if data is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "--data", json.dumps(data)]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def submit(prompt):
    body = {"prompt": prompt, "client_id": CLIENT}
    res = json.loads(api("/prompt", body))
    if "error" in res:
        raise RuntimeError("提交失败: " + json.dumps(res["error"], ensure_ascii=False))
    return res["prompt_id"]


def wait(prompt_id, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.loads(api(f"/history/{prompt_id}"))
        if prompt_id in h:
            node = h[prompt_id]
            if "status" in node and node["status"].get("status_str") == "error":
                msgs = node["status"].get("messages", [])
                raise RuntimeError("执行出错: " + json.dumps(msgs, ensure_ascii=False))
            return node
        time.sleep(4)
    raise TimeoutError("等待超时 (prompt_id=%s)" % prompt_id)


def download(node):
    files = []
    for nid, o in node.get("outputs", {}).items():
        for img in o.get("images", []):
            url = f"/view?filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img.get('type','')}"
            data = api(url, binary=True, timeout=180)
            path = os.path.join(OUTDIR, img["filename"])
            with open(path, "wb") as f:
                f.write(data)
            files.append(path)
            print("  已下载:", path, "(%d bytes)" % len(data))
    return files


def loaders():
    """共享加载器节点（GGUF + Qwen CLIP type）。"""
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": UNET}},
        # CLIPLoaderGGUF 用 type=qwen_image 才能正确加载 Qwen2.5-VL 的 GGUF（否则当成 SD1 CLIP 形状错）
        "2": {"class_type": "CLIPLoaderGGUF", "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "1a": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 1.73}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": None}},  # positive, 占位
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},    # negative
    }


def build_test():
    g = loaders()
    g["4"]["inputs"]["text"] = ("a cute chibi peach mascot character, round pink peach body, green leaf on top, "
                                "pink blush cheeks, big sparkling eyes, small smile, stubby arms and legs, "
                                "full body front view, standing, facing camera, clean light gray studio background, "
                                "Pixar 3D animation style, soft lighting, high detail")
    g["6"] = {"class_type": "QwenImageEmptyLatentImage",
              "inputs": {"width": 768, "height": 768, "aspect_ratio": "1:1",
                         "use_aspect_ratio": False, "batch_size": 1}}
    g["7"] = {"class_type": "QwenImageSampler",
              "inputs": {"model": ["1a", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
                         "seed": 20240724, "steps": 18, "cfg": 6.0, "sampler_name": "euler",
                         "scheduler": "normal", "denoise": 1.0}}
    g["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}
    g["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "peach_test"}}
    return g


def build_angle(positive, seed, denoise, prefix):
    g = loaders()
    g["4"]["inputs"]["text"] = positive
    g["6"] = {"class_type": "LoadImage", "inputs": {"image": ANCHOR}}
    g["6b"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["3", 0]}}
    g["7"] = {"class_type": "QwenImageSampler",
              "inputs": {"model": ["1a", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6b", 0],
                         "seed": seed, "steps": 20, "cfg": 6.0, "sampler_name": "euler",
                         "scheduler": "normal", "denoise": denoise}}
    g["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}
    g["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}}
    return g


# 4 个角度（denoise 略调以保一致；img2img 从 anchor 初始化）
ANGLES = [
    ("ref_front", 101, 0.55,
     "Keep this exact character's design identical (same pink peach body, smooth top, stubby arms and legs, big eyes). "
     "Generate a full-body FRONT view: standing upright, facing the camera, both short arms at sides, round pink peach "
     "body fully visible, cute face centered. Pixar style, soft clean light-gray studio background, no other objects."),
    ("ref_side", 202, 0.65,
     "Keep this exact character's design identical. Generate a full-body LEFT SIDE PROFILE view: we see the round body "
     "contour from the left, one stubby arm visible, smooth head top, the peach shape clearly readable. Pixar style, "
     "soft clean light-gray studio background, no other objects."),
    ("ref_back", 303, 0.65,
     "Keep this exact character's design identical. Generate a full-body BACK view: round pink peach body seen from "
     "behind, two small stubby legs visible at the bottom, smooth back of the head, no face visible. Pixar style, "
     "soft clean light-gray studio background, no other objects."),
    ("ref_expr_happy", 404, 0.6,
     "Keep this exact character's design identical. Generate a FRONT close-up of the face with a happy excited "
     "expression: big sparkly eyes, open smiling mouth, same pink peach head design, cheeks slightly flushed. "
     "Pixar style, soft clean light-gray studio background, no other objects."),
]


def run_one(prompt, label):
    print(f"[提交] {label} ...")
    pid = submit(prompt)
    print(f"  prompt_id={pid}")
    node = wait(pid)
    files = download(node)
    return files


def check_anchor():
    # ComfyUI 的 LoadImage 需要图在 ComfyUI 的 input/ 目录；脚本不依赖绝对路径，
    # 这里只给一个友好提示（anchor 是否就位由 ComfyUI 侧决定）。
    print(f"[提示] full 模式需要 ComfyUI 的 input/{ANCHOR} 就位（setup 脚本已自动拷贝，或手动上传）。")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    if mode == "test":
        run_one(build_test(), "txt2img 验证图 peach_test")
    elif mode == "full":
        check_anchor()
        all_files = []
        for aid, seed, denoise, pos in ANGLES:
            files = run_one(build_angle(pos, seed, denoise, "peach_" + aid), f"角度 {aid} (denoise={denoise})")
            all_files.extend(files)
        print("\n=== 全部完成 ===")
        for f in all_files:
            print(f)
    else:
        print("用法: python gen_refs_pai.py test|full")


if __name__ == "__main__":
    main()
