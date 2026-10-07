#!/usr/bin/env python3
"""Transform the FaceID 9-grid workflow into a regular-IPAdapter 9-grid workflow
(regular IPAdapter does not require human-face detection -> works for the hedgehog)."""
import json

SRC = "hedgehog_9grid_faceidplusv2_v2.json"
DST = "hedgehog_9grid_ipadapter.json"

with open(SRC, "r", encoding="utf-8") as f:
    wf = json.load(f)

# 1) node 8 (Canopus Pixar LoRA) must load from checkpoint (node 1), not the FaceID lora (node 80)
wf["8"]["inputs"]["model"] = ["1", 0]
wf["8"]["inputs"]["clip"] = ["1", 1]

# 2) node 10 -> regular IPAdapter (drop faceid-only inputs)
n10 = wf["10"]
n10["class_type"] = "IPAdapterAdvanced"
inp = n10["inputs"]
inp.pop("weight_faceidv2", None)
inp.pop("insightface", None)
inp["weight"] = 0.9
inp["weight_type"] = "linear"
inp["combine_embeds"] = "concat"
inp["embeds_scaling"] = "V only"
# ensure clip_vision present
inp["clip_vision"] = ["92", 0]
n10["_meta"]["title"] = "施加普通 IPAdapter（角色一致性）"

# 3) node 90 -> regular IPAdapter weight (plus-face, SDXL standard pair with clip_vision_g)
wf["90"]["inputs"]["ipadapter_file"] = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
wf["90"]["_meta"]["title"] = "加载普通 IPAdapter 权重"

# 4) add node 92 CLIPVisionLoader (regular IPAdapter needs clip_vision)
wf["92"] = {
    "class_type": "CLIPVisionLoader",
    "inputs": {"clip_name": "clip_vision_g.safetensors"},
    "_meta": {"title": "CLIP Vision 编码器"},
}

# 5) remove FaceID-only nodes: 80 (faceid lora) and 91 (insightface loader)
wf.pop("80", None)
wf.pop("91", None)

# 6) 同步「第3版测试图」的提示词（鼻子/耳朵修正 + IPAdapter 权重降到 0.8，给提示词更多控制）
NEW_NEG = ("realistic, photo, lowres, bad anatomy, extra limbs, extra ears, four ears, "
           "multiple ears, duplicate ears, asymmetric ears, ear tufts, cheek ears, "
           "pig, pig nose, snout, deformed, blurry, watermark, text, signature, "
           "human, person, boy, girl, child, dark, scary, multiple animals, "
           "duplicate, merged, overlapping, messy, rabbit, cat, dog, bear")
NEW_NOSE = "small cute round nose, tiny nose"
NEW_EARS = "exactly two small soft ears on top of head"

wf["10"]["inputs"]["weight"] = 0.95
wf["3"]["inputs"]["text"] = NEW_NEG

for nid in [str(i) for i in range(31, 40)]:
    if nid in wf and "text" in wf[nid].get("inputs", {}):
        t = wf[nid]["inputs"]["text"]
        t = t.replace("small black button nose", NEW_NOSE)
        t = t.replace("small soft quills on back, tiny legs",
                      "small soft quills on back, " + NEW_EARS + ", tiny legs")
        wf[nid]["inputs"]["text"] = t

with open(DST, "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

print("Wrote", DST)
print("nodes:", sorted(wf.keys()))
