# -*- coding: utf-8 -*-
"""验收镜头设置向导 → 提示词注入。"""
import json
import urllib.request

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8770/api"


def req(method, path, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, method=method,
                               headers={"Content-Type": "application/json"})
    with OP.open(r, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# 1) 直接用第1集的镜头3（id=90，双方提示词都较长，便于观察插点）
target = (90, req("GET", "/shots/90"))
print("目标镜头:", target[0], target[1].get("shot_code"))

# 2) 预览接口
prev = req("GET", f"/shots/{target[0]}/wizard-note?camera_shot=MS&angle=LOW_ANGLE&movement=DOLLY_IN&subject_position=%E4%B8%AD%E5%BF%83%C2%B7%E8%BF%91")
print("预览:", prev)

# 3) 注入
import copy
orig_img = (target[1]["detail"] or {}).get("image_prompt") or ""
orig_vid = (target[1]["detail"] or {}).get("video_prompt") or ""

r1 = req("POST", f"/shots/{target[0]}/apply-wizard",
         {"camera_shot": "MS", "angle": "LOW_ANGLE", "movement": "DOLLY_IN", "subject_position": "中心·近"})
print("\n[第1次注入]", r1["image"]["action"], "/", r1["video"]["action"])
print("  image:", r1["image"]["note"])
print("  video:", r1["video"]["note"])
print("  同一句是否只出现一次 image:", r1["image"]["prompt"].count(r1["image"]["note"]),
      " video:", r1["video"]["prompt"].count(r1["video"]["note"]))

# 4) 重复注入（换选项）→ 应该是 replaced，句子数不变
r2 = req("POST", f"/shots/{target[0]}/apply-wizard",
         {"camera_shot": "CU", "angle": "HIGH_ANGLE", "movement": "PAN", "subject_position": "右上"})
print("\n[第2次注入]", r2["image"]["action"], "/", r2["video"]["action"])
print("  image:", r2["image"]["note"])
print("  video:", r2["video"]["note"])
new_img, new_vid = r2["image"]["prompt"], r2["video"]["prompt"]
print("  旧句是否已消失:", r1["image"]["note"] not in new_img, r1["video"]["note"] not in new_vid)
print("  提示词长度 原→新 image:", len(orig_img), "→", len(new_img), " video:", len(orig_vid), "→", len(new_vid))
print("  ★视频正文里运镜: 出现次数 =", new_vid.count("运镜："), "（手写那句 + 我们的机位句，不应有第二个自动运镜）")
print("  ★冲突回执 pending_movement =", repr(r2["video"].get("pending_movement")))
print("  ★已有手写运镜 =", repr(r2["video"].get("existing_movement"))[:60])
print("  ★分镜图景别提醒 =", r2["image"].get("size_mentions"))
print("  ★分镜图里是否混入运镜:", ("运镜" in new_img))

print("\n--- image_prompt 前 260 字 ---")
print(new_img[:260])
print("\n--- video_prompt 前 260 字 ---")
print(new_vid[:260])

# 5) 清空运镜 → removed
r3 = req("POST", f"/shots/{target[0]}/apply-wizard",
         {"camera_shot": "CU", "angle": "HIGH_ANGLE", "movement": "", "subject_position": "右上"})
print("\n[清空运镜]", r3["video"]["action"], "->", repr(r3["video"]["note"]))

# 6) 还原成原始提示词
req("PATCH", f"/shots/{target[0]}",
    {"detail": {"image_prompt": orig_img, "video_prompt": orig_vid,
                "camera_shot": "", "angle": "", "movement": "", "subject_position": "",
                "camera_note": "", "wiz_image_note": "", "wiz_video_note": ""}})
back = req("GET", f"/shots/{target[0]}")
d2 = back["detail"]
print("\n还原校验:", (d2.get("image_prompt") or "") == orig_img, (d2.get("video_prompt") or "") == orig_vid)
