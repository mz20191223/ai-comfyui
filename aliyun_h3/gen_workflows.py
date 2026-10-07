# -*- coding: utf-8 -*-
"""从已验证底本生成 4 个 UI 格式工作流（拖入 ComfyUI 画布即用）"""
import json, os, shutil

OUT = r"D:\Aicomfyui\aliyun_h3\workflows"
os.makedirs(OUT, exist_ok=True)

def ui_nodes_skeleton():
    return {"last_node_id": 0, "last_link_id": 0, "nodes": [], "links": [],
            "groups": [], "config": {}, "extra": {}, "version": 0.4, "seed": 0,
            "extra_data": {}, "meta": {"format": "wf"}}

def add_node(wf, nid, ntype, title, pos, widgets, inputs, outputs):
    wf["nodes"].append({
        "id": nid, "type": ntype, "pos": pos, "size": [280, 60], "flags": {},
        "order": nid, "mode": 0, "inputs": inputs, "outputs": outputs,
        "title": title, "properties": {"Node name for S&R": ntype},
        "widgets_values": widgets})
    wf["last_node_id"] = max(wf["last_node_id"], nid)

def add_link(wf, link_id, src_id, src_slot, dst_id, dst_slot, typ):
    wf["links"].append([link_id, src_id, src_slot, dst_id, dst_slot, typ])
    wf["last_link_id"] = max(wf["last_link_id"], link_id)
    for n in wf["nodes"]:
        if n["id"] == src_id:
            n["outputs"][src_slot].setdefault("links", []).append(link_id)
        if n["id"] == dst_id:
            n["inputs"][dst_slot]["link"] = link_id

def o(name, typ, slot):
    return {"name": name, "type": typ, "links": [], "slot_index": slot}

def i(name, typ, slot, link=None):
    return {"name": name, "type": typ, "link": link, "slot_index": slot}

# ============ 工作流 1：LLM 扩写流 ============
wf = ui_nodes_skeleton()
add_node(wf, 1, "String Literal", "用户输入(中文短词)", [100, 0],
         ["一只皮克斯风格的兔子，大眼睛，毛茸茸"], [], [o("STRING", "STRING", 0)])
add_node(wf, 2, "LlamaCPPModelLoader", "加载Qwen2.5-14B GGUF", [400, 0],
         ["qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf", "qwen2", "None"], [],
         [o("model", "LLM_MODEL", 0)])
add_node(wf, 3, "LlamaCPPOptions", "LLM推理参数(GPU)", [700, 0],
         [-1, 4096, -1, -1, 512, 512, 0, True, False, True, False, False, False, False, False, False, False], [],
         [o("options", "LLM_OPTIONS", 0)])
add_node(wf, 4, "LlamaCPPEngine", "LLM扩写提示词", [1000, 0],
         ["", "You are a professional image-generation prompt engineer. Rewrite the user's short Chinese description into a detailed, vivid English prompt for a text-to-image model. Include: subject, style, lighting, composition, materials, color palette, background, mood. Output ONLY the prompt text, no extra explanation.",
          "close", "text", 400, 0.7, 0.95, 100, 1.0, -1],
         [i("model", "LLM_MODEL", 0), i("prompt", "STRING", 1), i("image", "IMAGE", 2, None), i("options", "LLM_OPTIONS", 3)],
         [o("response", "STRING", 0)])
add_node(wf, 5, "LlamaCPPMemoryCleanup", "释放LLM显存", [100, 300],
         ["close", ""], [i("memory_cleanup", "COMBO", 0), i("passthrough", "STRING", 1)],
         [o("passthrough", "STRING", 0)])
add_node(wf, 6, "ShowText", "扩写结果(复制到角色图流)", [1300, 0],
         [""], [i("text", "STRING", 0)], [])
add_link(wf, 1, 1, 0, 4, 1, "STRING")
add_link(wf, 2, 2, 0, 4, 0, "LLM_MODEL")
add_link(wf, 3, 3, 0, 4, 3, "LLM_OPTIONS")
add_link(wf, 4, 4, 0, 5, 1, "STRING")
add_link(wf, 5, 4, 0, 6, 0, "STRING")
wf["title"] = "① 扩写流：短词 → 英文提示词 (Qwen2.5-14B)"
with open(os.path.join(OUT, "wf_01_llm_expand.json"), "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=1)

# ============ 工作流 2：Flux 角色图流 ============
wf = ui_nodes_skeleton()
add_node(wf, 1, "String Literal", "英文提示词(来自扩写流)", [100, 0],
         ["A cute 3D Pixar-style rabbit with big sparkling eyes, fluffy fur, soft studio lighting, pastel background"], [],
         [o("STRING", "STRING", 0)])
add_node(wf, 2, "UnetLoaderGGUF", "Flux unet GGUF", [400, 0],
         ["flux1-dev-Q4_K_S.gguf"], [], [o("MODEL", "MODEL", 0)])
add_node(wf, 3, "DualCLIPLoader", "双编码器(t5xxl+clip_l)", [700, 0],
         ["t5xxl_fp8_e4m3fn.safetensors", "clip_l.safetensors", "flux", "default"], [],
         [o("CLIP", "CLIP", 0)])
add_node(wf, 4, "VAELoader", "加载VAE(ae)", [1000, 0],
         ["ae.safetensors"], [], [o("VAE", "VAE", 0)])
add_node(wf, 5, "EmptyLatentImage", "空白潜空间 1024x1024", [1300, 0],
         [1024, 1024, 1], [], [o("LATENT", "LATENT", 0)])
add_node(wf, 6, "CLIPTextEncode", "正提示词", [100, 200],
         [""], [i("clip", "CLIP", 0), i("text", "STRING", 1)], [o("CONDITIONING", "CONDITIONING", 0)])
add_node(wf, 7, "String Literal", "负提示词", [400, 200],
         ["low quality, blurry, deformed, extra limbs, watermark"], [], [o("STRING", "STRING", 0)])
add_node(wf, 8, "CLIPTextEncode", "负提示词编码", [700, 200],
         [""], [i("clip", "CLIP", 0), i("text", "STRING", 1)], [o("CONDITIONING", "CONDITIONING", 0)])
add_node(wf, 9, "KSampler", "采样", [1000, 200],
         [25, 3.5, 0, "euler", "simple", 1.0],
         [i("model", "MODEL", 0), i("positive", "CONDITIONING", 1), i("negative", "CONDITIONING", 2), i("latent_image", "LATENT", 3)],
         [o("LATENT", "LATENT", 0)])
add_node(wf, 10, "VAEDecode", "解码", [1300, 200],
         [], [i("samples", "LATENT", 0), i("vae", "VAE", 1)], [o("IMAGE", "IMAGE", 0)])
add_node(wf, 11, "SaveImage", "保存角色设定图", [100, 400],
         ["char_role"], [i("images", "IMAGE", 0)], [])
add_link(wf, 1, 1, 0, 6, 1, "STRING")
add_link(wf, 2, 2, 0, 9, 0, "MODEL")
add_link(wf, 3, 3, 0, 6, 0, "CLIP")
add_link(wf, 4, 3, 0, 8, 0, "CLIP")
add_link(wf, 5, 4, 0, 10, 1, "VAE")
add_link(wf, 6, 5, 0, 9, 3, "LATENT")
add_link(wf, 7, 6, 0, 9, 1, "CONDITIONING")
add_link(wf, 8, 7, 0, 8, 1, "STRING")
add_link(wf, 9, 8, 0, 9, 2, "CONDITIONING")
add_link(wf, 10, 9, 0, 10, 0, "LATENT")
add_link(wf, 11, 10, 0, 11, 0, "IMAGE")
wf["title"] = "② 角色图流：英文提示词 → 角色设定图 (Flux)"
with open(os.path.join(OUT, "wf_02_flux_char.json"), "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=1)

# ============ 工作流 3：Qwen-Edit 分镜图流（参考锁角色） ============
wf = ui_nodes_skeleton()
add_node(wf, 1, "UnetLoaderGGUF", "Qwen-Image-Edit GGUF", [100, 0],
         ["qwen-image-edit-2511-Q4_K_M.gguf"], [], [o("MODEL", "MODEL", 0)])
add_node(wf, 2, "CLIPLoaderGGUF", "文本编码器(Qwen2.5-VL)", [400, 0],
         ["Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf", "qwen_image"], [], [o("CLIP", "CLIP", 0)])
add_node(wf, 3, "VAELoader", "加载VAE", [700, 0],
         ["qwen_image_vae.safetensors"], [], [o("VAE", "VAE", 0)])
add_node(wf, 4, "ModelSamplingAuraFlow", "Qwen-Image采样shift", [1000, 0],
         [1.73], [i("model", "MODEL", 0)], [o("MODEL", "MODEL", 0)])
add_node(wf, 5, "LoraLoader", "多角度LoRA", [1300, 0],
         ["qwen-image-edit-2511-multiple-angles-lora.safetensors", 0.9, 0],
         [i("model", "MODEL", 0), i("clip", "CLIP", 1)], [o("MODEL", "MODEL", 0), o("CLIP", "CLIP", 0)])
add_node(wf, 6, "LoadImage", "角色参考图(选第一张设定图)", [100, 300],
         ["char_role_00001_.png"], [], [o("IMAGE", "IMAGE", 0)])
add_node(wf, 7, "TextEncodeQwenImageEditPlus", "分镜条件编码", [400, 300],
         ["<sks> front view eye-level shot medium shot. The SAME cute 3D chibi character from the reference image, same identity and art style, standing in a sunny meadow with flowers, dynamic pose, soft warm lighting, clean background. Keep identical character design."],
         [i("clip", "CLIP", 0), i("prompt", "STRING", 1), i("image1", "IMAGE", 2), i("vae", "VAE", 3)],
         [o("CONDITIONING", "CONDITIONING", 0)])
add_node(wf, 8, "CLIPTextEncode", "负提示词", [700, 300],
         [""], [i("clip", "CLIP", 0), i("text", "STRING", 1)], [o("CONDITIONING", "CONDITIONING", 0)])
add_node(wf, 9, "VAEEncode", "参考图入潜空间", [1000, 300],
         [], [i("pixels", "IMAGE", 0), i("vae", "VAE", 1)], [o("LATENT", "LATENT", 0)])
add_node(wf, 10, "KSampler", "采样(denoise 0.8)", [1300, 300],
         [12345, 35, 7.5, "dpmpp_2m", "karras", 0.8],
         [i("model", "MODEL", 0), i("positive", "CONDITIONING", 1), i("negative", "CONDITIONING", 2), i("latent_image", "LATENT", 3)],
         [o("LATENT", "LATENT", 0)])
add_node(wf, 11, "VAEDecode", "解码", [100, 500],
         [], [i("samples", "LATENT", 0), i("vae", "VAE", 1)], [o("IMAGE", "IMAGE", 0)])
add_node(wf, 12, "SaveImage", "保存分镜图", [400, 500],
         ["storyboard"], [i("images", "IMAGE", 0)], [])
add_link(wf, 1, 1, 0, 4, 0, "MODEL")
add_link(wf, 2, 4, 0, 5, 0, "MODEL")
add_link(wf, 3, 2, 0, 5, 1, "CLIP")
add_link(wf, 4, 2, 0, 7, 0, "CLIP")
add_link(wf, 5, 2, 0, 8, 0, "CLIP")
add_link(wf, 6, 3, 0, 7, 3, "VAE")
add_link(wf, 7, 3, 0, 9, 1, "VAE")
add_link(wf, 8, 3, 0, 11, 1, "VAE")
add_link(wf, 9, 6, 0, 7, 2, "IMAGE")
add_link(wf, 10, 6, 0, 9, 0, "IMAGE")
add_link(wf, 11, 5, 0, 10, 0, "MODEL")
add_link(wf, 12, 7, 0, 10, 1, "CONDITIONING")
add_link(wf, 13, 8, 0, 10, 2, "CONDITIONING")
add_link(wf, 14, 9, 0, 10, 3, "LATENT")
add_link(wf, 15, 10, 0, 11, 0, "LATENT")
add_link(wf, 16, 11, 0, 12, 0, "IMAGE")
wf["title"] = "③ 分镜图流：角色参考图+分镜提示词 → 分镜图 (Qwen-Edit锁角色)"
with open(os.path.join(OUT, "wf_03_qwen_edit_storyboard.json"), "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=1)

# ============ 工作流 4：官方 H3 视频模板（复制+改名） ============
src = r"D:\Aicomfyui\aliyun_h3\workflows"
renames = {
    "video_minimax_h3_t2v.json": "wf_04a_h3_t2v.json",
    "video_minimax_h3_i2v.json": "wf_04b_h3_i2v.json",
    "video_minimax_h3_r2v.json": "wf_04c_h3_r2v.json",
}
for old, new in renames.items():
    p = os.path.join(src, old)
    if os.path.exists(p):
        shutil.copy(p, os.path.join(src, new))
        print("copied", new)

# 校验所有生成的 JSON
for f in sorted(os.listdir(OUT)):
    if f.endswith(".json"):
        with open(os.path.join(OUT, f), encoding="utf-8") as fh:
            json.load(fh)
        print("OK", f)
print("全部生成完成")
