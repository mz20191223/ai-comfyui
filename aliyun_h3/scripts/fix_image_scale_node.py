import json
import os

src = r"D:\Aicomfyui\aliyun_h3\workflows\nunchaku-qwen-image-edit-2509-lightning.json"
dst = r"D:\Aicomfyui\aliyun_h3\workflows\nunchaku-qwen-image-edit-2509-lightning-fix.json"

with open(src, "r", encoding="utf-8") as f:
    wf = json.load(f)

fixed = False
for node in wf.get("nodes", []):
    if node.get("type") == "ImageScaleToTotalPixels":
        node["type"] = "ImageScale"
        node.setdefault("properties", {})
        node["properties"]["Node name for S&R"] = "ImageScale"
        # 原节点把图缩放到约 1MP；改用 ImageScale 固定 1024x1024 center crop，等效
        node["widgets_values"] = ["lanczos", 1024, 1024, "center"]
        print(f"fixed node id={node['id']}: ImageScaleToTotalPixels -> ImageScale")
        fixed = True

if not fixed:
    print("WARNING: no ImageScaleToTotalPixels node found")

with open(dst, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)

print(f"wrote {dst}")
