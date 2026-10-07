"""生成「一键 9 路并联」工作流：点一次 Queue Prompt 出 9 张不同角度/表情的同一刺猬。
共享 IP-Adapter（锁脸）+ ControlNet OpenPose（锁姿势）；9 路各用不同姿势图+表情 prompt。
最后 9 张图本地用 assemble_grid.py 拼成 3x3 设定表。
"""
import json

POS = [
    ("01_front_neutral",        "calm neutral expression, front facing viewer"),
    ("02_3q_left",              "calm neutral expression, three quarter view turning left"),
    ("03_3q_right",             "calm neutral expression, three quarter view turning right"),
    ("04_side_left",            "calm neutral expression, left side profile"),
    ("05_side_right",           "calm neutral expression, right side profile"),
    ("06_back",                 "calm neutral expression, viewed from behind, back turned"),
    ("07_happy_arms_up",        "big cheerful smile, joyful, arms raised up happily"),
    ("08_surprised_hands_face", "surprised expression, eyes wide, mouth open, hands near face"),
    ("09_wink_hand_hip",        "cute wink, playful smile, one hand on hip waving"),
]

BASE_POS = ("pixar style, disney pixar, 3d cartoon character, a cute baby hedgehog, "
            "round plump body, small soft quills on back, tiny legs, large sparkling glossy eyes, "
            "small black button nose, smooth clay skin between quills, solid pastel light blue clean "
            "background, full body shot, centered, soft studio lighting, octane render, 8k uhd, "
            "masterpiece, best quality, ")

NEG = ("realistic, photo, lowres, bad anatomy, extra limbs, deformed, blurry, watermark, text, "
       "signature, human, person, boy, girl, child, dark, scary, multiple animals, duplicate, "
       "merged, overlapping, messy, rabbit, cat, dog, bear")

wf = {}
wf["1"] = {"class_type": "CheckpointLoaderSimple",
           "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
           "_meta": {"title": "加载 SDXL 基座"}}
wf["8"] = {"class_type": "LoraLoader",
           "inputs": {"lora_name": "Canopus-Pixar-Art.safetensors", "strength_model": 0.8,
                      "strength_clip": 0.8, "model": ["1", 0], "clip": ["1", 1]},
           "_meta": {"title": "Canopus Pixar LoRA"}}
wf["9"] = {"class_type": "IPAdapterUnifiedLoader",
           "inputs": {"model": ["8", 0], "clip_vision_name": "clip_vision_g.safetensors",
                      "ipadapter_name": "ip-adapter-plus-face_sdxl_vit-h.safetensors"},
           "_meta": {"title": "IP-Adapter 统一加载（锁脸）"}}
wf["11"] = {"class_type": "LoadImage", "inputs": {"image": "hedgehog_hero.png"},
            "_meta": {"title": "IP-Adapter 参照图（最满意的刺猬）"}}
wf["10"] = {"class_type": "IPAdapter",
            "inputs": {"ipadapter": ["9", 2], "image": ["11", 0], "model": ["9", 0],
                       "weight": 0.9, "noise": 0.0, "weight_type": "linear",
                       "start_at": 0.0, "end_at": 1.0, "unfold_batch": False, "embeds_scaling": "V only"},
            "_meta": {"title": "施加 IP-Adapter"}}
wf["12"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "OpenPoseXL2.safetensors"},
            "_meta": {"title": "ControlNet OpenPose"}}
wf["3"] = {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["9", 1]},
           "_meta": {"title": "负提示词"}}
wf["4"] = {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1152, "batch_size": 1},
           "_meta": {"title": "空 Latent 1024x1152"}}

SEED = 246813579
for i, (pose, expr) in enumerate(POS, start=1):
    pose_n = 20 + i
    pos_n = 30 + i
    cnet_n = 40 + i
    ks_n = 50 + i
    vae_n = 60 + i
    save_n = 70 + i

    wf[str(pose_n)] = {"class_type": "LoadImage", "inputs": {"image": f"{pose}.png"},
                       "_meta": {"title": f"姿势骨架 {pose}"}}
    wf[str(pos_n)] = {"class_type": "CLIPTextEncode",
                      "inputs": {"text": BASE_POS + expr, "clip": ["9", 1]},
                      "_meta": {"title": f"正提示词 {i}（{expr[:18]}）"}}
    wf[str(cnet_n)] = {"class_type": "ControlNetApplyAdvanced",
                       "inputs": {"positive": [str(pos_n), 0], "negative": ["3", 0],
                                  "control_net": ["12", 0], "image": [str(pose_n), 0],
                                  "strength": 0.8, "start_percent": 0.0, "end_percent": 1.0},
                       "_meta": {"title": f"ControlNet {i}"}}
    wf[str(ks_n)] = {"class_type": "KSampler",
                     "inputs": {"seed": SEED, "steps": 30, "cfg": 6.0, "sampler_name": "dpmpp_2m",
                                "scheduler": "karras", "denoise": 1.0, "model": ["10", 0],
                                "positive": [str(cnet_n), 0], "negative": [str(cnet_n), 1],
                                "latent_image": ["4", 0]},
                     "_meta": {"title": f"KSampler {i}"}}
    wf[str(vae_n)] = {"class_type": "VAEDecode", "inputs": {"samples": [str(ks_n), 0], "vae": ["1", 2]},
                      "_meta": {"title": f"VAE {i}"}}
    wf[str(save_n)] = {"class_type": "SaveImage",
                       "inputs": {"images": [str(vae_n), 0], "filename_prefix": pose},
                       "_meta": {"title": f"保存 {i}"}}

out = r"C:\Users\Administrator\WorkBuddy\2026-07-15-13-21-24\hedgehog_9grid_onerun_workflow.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)
print("nodes:", len(wf), "->", out)
