#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把原 9 宫格工作流的 vit-h IPAdapter 部分，替换为 FaceID Plus v2 显式三件套节点。
节点链：
  1 CheckpointLoaderSimple
  -> 80 LoraLoader(plusv2 lora, model only)
  -> 8  LoraLoader(Canopus Pixar, model+clip)   # CLIP=[8,1]
  -> 90 IPAdapterModelLoader(plusv2 .bin)        # ipadapter=[90,0]
  -> 91 IPAdapterInsightFaceLoader(CUDA)         # insightface=[91,0]
  11 LoadImage(hedgehog_hero)
  -> 10 IPAdapterFaceID(model=[8,0], ipadapter=[90,0], image=[11,0], insightface=[91,0], weight, weight_faceidv2)
      -> 输出 [10,0] 供给 9 个 KSampler 的 model
  所有 CLIPTextEncode 的 clip 由 [9,1] 改为 [8,1]
"""
import json

SRC = "hedgehog_9grid_onerun_workflow.json"

with open(SRC, encoding="utf-8") as f:
    wf = json.load(f)

# 1) 插入 plusv2 lora 加载器（节点 80），放在 checkpoint(1) 与 Canopus lora(8) 之间
wf["80"] = {
    "class_type": "LoraLoader",
    "inputs": {
        "lora_name": "ip-adapter-faceid-plusv2_sdxl_lora.safetensors",
        "strength_model": 0.8,
        "strength_clip": 0.0,
        "model": ["1", 0],
        "clip": ["1", 1],
    },
    "_meta": {"title": "FaceID Plus v2 LoRA (model only)"},
}

# 2) Canopus LoraLoader(8)：输入改为来自 80
wf["8"]["inputs"]["model"] = ["80", 0]
wf["8"]["inputs"]["clip"] = ["80", 1]

# 3) 删除旧 IPAdapterUnifiedLoader(9)
if "9" in wf:
    del wf["9"]

# 4) 新增 IPAdapterModelLoader(90) 加载 plusv2 .bin
wf["90"] = {
    "class_type": "IPAdapterModelLoader",
    "inputs": {
        "ipadapter_file": "ip-adapter-faceid-plusv2_sdxl.bin",
    },
    "_meta": {"title": "加载 FaceID Plus v2 权重 .bin"},
}

# 5) 新增 IPAdapterInsightFaceLoader(91)
wf["91"] = {
    "class_type": "IPAdapterInsightFaceLoader",
    "inputs": {
        "provider": "CUDA",
        "model_name": "antelopev2",
    },
    "_meta": {"title": "InsightFace 加载（人脸嵌入）"},
}

# 6) 改写节点 10 为 IPAdapterFaceID（FaceID Plus v2 施加）
wf["10"] = {
    "class_type": "IPAdapterFaceID",
    "inputs": {
        "model": ["8", 0],
        "ipadapter": ["90", 0],
        "image": ["11", 0],
        "weight": 1.0,
        "weight_faceidv2": 1.0,
        "weight_type": "linear",
        "combine_embeds": "concat",
        "start_at": 0.0,
        "end_at": 1.0,
        "embeds_scaling": "V only",
        "insightface": ["91", 0],
    },
    "_meta": {"title": "施加 FaceID Plus v2（锁脸）"},
}

# 7) 所有 CLIPTextEncode 的 clip 引用 [9,1] -> [8,1]
for nid, node in wf.items():
    if node.get("class_type") == "CLIPTextEncode":
        c = node["inputs"].get("clip")
        if isinstance(c, list) and c[0] == "9" and c[1] == 1:
            node["inputs"]["clip"] = ["8", 1]

# 8) 9 个 KSampler 的 model 仍引用 [10,0]（原样，无需改）

with open("hedgehog_9grid_faceidplusv2_v2.json", "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

# ---- 生成单图测试版（仅 pose 01 那一路 + 共享链）----
keep = {"1", "80", "8", "90", "91", "11", "10", "12", "3", "4",
        "21", "31", "41", "51", "61", "71"}
test = {k: v for k, v in wf.items() if k in keep}
with open("hedgehog_faceid_v2_test.json", "w", encoding="utf-8") as f:
    json.dump(test, f, ensure_ascii=False, indent=2)

print("OK -> hedgehog_9grid_faceidplusv2_v2.json (9-grid)")
print("OK -> hedgehog_faceid_v2_test.json (single-image test)")
# 自检：确认没有残留 [9, 的引用
bad = [k for k, v in wf.items()
       if json.dumps(v).find('"9", 1') >= 0 or json.dumps(v).find('"9", 0') >= 0
       or json.dumps(v).find('"9",0') >= 0 or json.dumps(v).find('"9",1') >= 0]
print("残留 [9,?] 引用节点:", bad if bad else "无")
print("IPAdapterFaceID 节点10 inputs:", json.dumps(wf["10"]["inputs"], ensure_ascii=False))
