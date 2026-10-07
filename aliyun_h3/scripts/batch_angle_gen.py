#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen-Image-Edit 多角度批量出图脚本 (ComfyUI API)

作用: 把"一个角色 x 一个角度 = 手动跑一次"的重复劳动自动化。
      一次提交 [角色 x 角度] 的所有组合, ComfyUI 后台自动排队生成, 人不用守着。

前提:
  1. 生图实例 dsw-831216 已启动 ComfyUI (端口 8188), 本脚本在该实例内部运行。
  2. 本脚本和 wf_03_qwen_edit_storyboard.json 放在同一目录。
  3. 三个角色的白底正脸参考图已传到 ComfyUI 的 input 目录, 命名如下:
       阿乐: ale_ref_front_00001_.png
       果果: guoguo_ref_front_00001_.png
       老彭: laopeng_ref_front_00001_.png

运行:
  cd 脚本目录
  python3 batch_angle_gen.py
  (建议后台: nohup python3 batch_angle_gen.py > batch.log 2>&1 &)

依赖: 仅 Python 标准库 (urllib / json / time), 无需 pip install。

参数调整:
  ROLES   - 角色列表 (参考图文件名)
  ANGLES  - 角度列表 (方位词 prompt, 必须带 <sks> 前缀)
  BASE_SEED - 起始种子, 每组合自动 +1, 保证每张不同
"""

import json
import time
import urllib.request
import urllib.error

COMFY_URL = "http://127.0.0.1:8188"
WF_FILE = "wf_03_qwen_edit_storyboard.json"   # UI 格式工作流

# 角色 -> 白底正脸参考图 (放在 ComfyUI/input/ 下)
ROLES = [
    {"name": "ale",     "ref": "ale_ref_front_00001_.png"},
    {"name": "guoguo",  "ref": "guoguo_ref_front_00001_.png"},
    {"name": "laopeng", "ref": "laopeng_ref_front_00001_.png"},
]

# 角度 -> 方位词 (fal Multiple-Angles LoRA 固定格式: <sks> [方位] [仰角] [距离])
# 只采用 fal 官方示例词: front / front-right / right / back
#   (back-right / front-left 非官方词, LoRA 会退化成 right side, 已弃用)
# 正面 front 直接用白底正脸参考图 (ale_ref_front 等), 此处只生成其余 3 个角度
ANGLES = [
    ("fr45",   "<sks> front-right quarter view eye-level shot medium shot"),
    ("right",  "<sks> right side view eye-level shot medium shot"),
    ("back",   "<sks> back view eye-level shot medium shot"),
]

BASE_SEED = 20260811

# 跳过的 hidden 输入 (前端上传专用, API 不需要)
SKIP_INPUTS = ("upload",)


def http_json(url, data=None, method="GET", timeout=300):
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def get_object_info():
    return http_json(COMFY_URL + "/object_info")["object_info"]


def ui_to_api(ui, object_info):
    """把 ComfyUI UI 格式工作流转成 API (精简) 格式。"""
    links = {l[0]: l for l in ui["links"]}
    api = {}
    for n in ui["nodes"]:
        ct = n["type"]
        info = object_info.get(ct, {})
        req = info.get("input", {}).get("required", {})
        opt = info.get("input", {}).get("optional", {})

        # 已连线的输入: [源节点id, 源slot]
        linked = {}
        for inp in n.get("inputs", []):
            if inp.get("link") is not None and inp["link"] in links:
                l = links[inp["link"]]
                linked[inp["name"]] = [l[1], l[2]]

        inputs = {}
        wv = n.get("widgets_values", [])
        wi = 0
        for name in list(req.keys()) + list(opt.keys()):
            if name in SKIP_INPUTS:
                continue
            if name in linked:
                inputs[name] = linked[name]
                continue
            if wi < len(wv):
                inputs[name] = wv[wi]
                wi += 1
            else:
                # 取 object_info 默认值, 兜底
                spec = req.get(name, opt.get(name, [None]))
                default = spec[-1] if isinstance(spec, (list, tuple)) and spec else spec
                if isinstance(default, dict) and "default" in default:
                    inputs[name] = default["default"]
                else:
                    inputs[name] = default
        api[str(n["id"])] = {"class_type": ct, "inputs": inputs}
    return api


def find_node(api, ctype):
    for nid, n in api.items():
        if n["class_type"] == ctype:
            return nid, n
    return None, None


def main():
    print("连接 ComfyUI:", COMFY_URL)
    object_info = get_object_info()
    ui = json.load(open(WF_FILE, encoding="utf-8"))
    base_api = ui_to_api(ui, object_info)
    print("工作流解析完成, 节点数:", len(base_api))

    tasks = []
    idx = 0
    for role in ROLES:
        for angle_key, angle_prompt in ANGLES:
            idx += 1
            api = json.loads(json.dumps(base_api))  # 深拷贝
            _, load = find_node(api, "LoadImage")
            load["inputs"]["image"] = role["ref"]
            _, enc = find_node(api, "TextEncodeQwenImageEditPlus")
            enc["inputs"]["prompt"] = angle_prompt
            _, ks = find_node(api, "KSampler")
            ks["inputs"]["seed"] = BASE_SEED + idx
            _, save = find_node(api, "SaveImage")
            save["inputs"]["filename_prefix"] = f"{role['name']}_{angle_key}"
            tasks.append((f"{role['name']}_{angle_key}", api))

    print(f"共 {len(tasks)} 个任务 (角色 x 角度)")

    submitted = []
    for prefix, api in tasks:
        body = json.dumps({"prompt": api}).encode("utf-8")
        try:
            resp = http_json(COMFY_URL + "/prompt", data=body, method="POST")
            pid = resp.get("prompt_id")
            submitted.append((prefix, pid))
            print(f"  [提交] {prefix} -> {pid}")
        except Exception as e:
            print(f"  [失败] {prefix}: {e}")
        time.sleep(0.3)

    print(f"已全部提交 {len(submitted)} 个, ComfyUI 后台排队生成中...")

    # 等待全部完成并汇报输出文件
    done = {}
    while len(done) < len(submitted):
        time.sleep(5)
        try:
            hist = http_json(COMFY_URL + "/history")
        except Exception:
            continue
        for pid, data in hist.items():
            if pid in [s[1] for s in submitted] and pid not in done:
                done[pid] = data
                prefix = next(p for p, i in submitted if i == pid)
                # 提取 SaveImage 输出文件名
                files = []
                for out in data.get("outputs", {}).values():
                    for img in out.get("images", []):
                        files.append(img.get("filename"))
                print(f"  [完成] {prefix}: {files}")

    print("所有角度图生成完毕, 在 ComfyUI/output/ 下查看。")


if __name__ == "__main__":
    main()
