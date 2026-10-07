# -*- coding: utf-8 -*-
"""备选工作流：当 HAI 插件没有 IPAdapterModelLoader 时，改用 IPAdapterUnifiedLoaderFaceID
(preset='FACEID PLUS V2') 一次性加载 plusv2 的 .bin + lora，再接 IPAdapterFaceID 注入人脸。
与三件套版(hedgehog_9grid_faceidplusv2_v2.json)互为保险：开 HAI 后探测到缺 IPAdapterModelLoader 即用此版。
"""
import json

SRC = "hedgehog_9grid_onerun_workflow.json"
with open(SRC, encoding="utf-8") as f:
    wf = json.load(f)

# 删除旧 IPAdapterUnifiedLoader(9)
if "9" in wf:
    del wf["9"]

# 90: UnifiedLoaderFaceID（预设加载 plusv2 .bin + 施加 lora）
wf["90"] = {
    "class_type": "IPAdapterUnifiedLoaderFaceID",
    "inputs": {
        "model": ["1", 0],
        "preset": "FACEID PLUS V2",
        "lora_strength": 0.8,
        "provider": "CUDA",
    },
    "_meta": {"title": "FaceID Plus v2 预设加载 (UnifiedLoader)"},
}

# 8: Canopus LoraLoader —— model 接 UnifiedLoader 输出的 MODEL，clip 接 checkpoint 的 CLIP
wf["8"]["inputs"]["model"] = ["90", 0]
wf["8"]["inputs"]["clip"] = ["1", 1]

# 91: InsightFace 加载
wf["91"] = {
    "class_type": "IPAdapterInsightFaceLoader",
    "inputs": {"provider": "CUDA", "model_name": "antelopev2"},
    "_meta": {"title": "InsightFace 加载（人脸嵌入）"},
}

# 10: IPAdapterFaceID —— ipadapter 接 UnifiedLoader 第二输出 [90,1]
wf["10"] = {
    "class_type": "IPAdapterFaceID",
    "inputs": {
        "model": ["8", 0],
        "ipadapter": ["90", 1],
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

# CLIPTextEncode 的 clip 引用 [9,?] -> [8,1]
for nid, node in wf.items():
    if node.get("class_type") == "CLIPTextEncode":
        c = node["inputs"].get("clip")
        if isinstance(c, list) and c[0] == "9":
            node["inputs"]["clip"] = ["8", 1]

with open("hedgehog_9grid_faceidplusv2_alt.json", "w", encoding="utf-8") as f:
    json.dump(wf, f, ensure_ascii=False, indent=2)

# 单图测试版（备选）
keep = {"1", "8", "90", "91", "11", "10", "12", "3", "4",
        "21", "31", "41", "51", "61", "71"}
test = {k: v for k, v in wf.items() if k in keep}
with open("hedgehog_faceid_v2_test_alt.json", "w", encoding="utf-8") as f:
    json.dump(test, f, ensure_ascii=False, indent=2)

# 自检
bad = [k for k, v in wf.items() if json.dumps(v).find('"9", 1') >= 0 or json.dumps(v).find('"9", 0') >= 0]
print("OK -> hedgehog_9grid_faceidplusv2_alt.json (9-grid, UnifiedLoaderFaceID 备选)")
print("OK -> hedgehog_faceid_v2_test_alt.json (single test, 备选)")
print("残留 [9,?] 引用:", bad if bad else "无")
