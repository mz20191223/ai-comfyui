import json

SRC = "hedgehog_9grid_onerun_workflow.json"
OUT = "hedgehog_9grid_faceidplusv2_workflow.json"

with open(SRC, "r", encoding="utf-8") as f:
    wf = json.load(f)

# 1) node 9: IPAdapterUnifiedLoader -> CLIPVisionLoader
wf["9"] = {
    "class_type": "CLIPVisionLoader",
    "inputs": {"clip_name": "clip_vision_g.safetensors"},
    "_meta": {"title": "加载 CLIP Vision G（FaceID Plus v2 需要）"}
}

# 2) node 10: IPAdapter -> IPAdapterFaceIDPlus
wf["10"] = {
    "class_type": "IPAdapterFaceIDPlus",
    "inputs": {
        "ipadapter": "ip-adapter-faceid-plusv2_sdxl.bin",
        "lora": "ip-adapter-faceid-plusv2_sdxl_lora.safetensors",
        "model": ["8", 0],
        "clip_vision": ["9", 0],
        "image": ["11", 0],
        "weight": 0.9,
        "noise": 0.0,
        "weight_type": "linear",
        "start_at": 0.0,
        "end_at": 1.0,
        "unfold_batch": False,
        "embeds_scaling": "V only"
    },
    "_meta": {"title": "施加 IP-Adapter FaceID Plus v2（锁定同一张脸）"}
}

# 3) 所有 CLIPTextEncode 的 clip 从 ["9",1] 改回 ["8",1]（Canopus LoRA 的 clip）
changed = 0
for nid, node in wf.items():
    if node.get("class_type") == "CLIPTextEncode":
        clip = node["inputs"].get("clip")
        if clip == ["9", 1]:
            node["inputs"]["clip"] = ["8", 1]
            changed += 1

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print("written ->", OUT)
print("CLIPTextEncode clip fixed:", changed)
print("node9 class:", wf["9"]["class_type"])
print("node10 class:", wf["10"]["class_type"], "| ipadapter:", wf["10"]["inputs"]["ipadapter"], "| lora:", wf["10"]["inputs"]["lora"])
