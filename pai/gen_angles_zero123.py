#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 ComfyUI-Zero123-Porting 从参考图出 4 个严格角度（前/左/后/右）。
依赖: DSW 已装 ComfyUI-Zero123-Porting 节点 + models/checkpoints/zero123/stable-zero123.ckpt
参考图: ComfyUI input/peach_role_v6.png (或 REF_IMG 环境变量指定)
输出: ./out_zero123/z123_*.png (256x256, 后续放大)

用法(DSW Terminal, pai 目录):
  python gen_angles_zero123.py
"""
import subprocess, json, os, sys, time, uuid

COMFY_IP = os.environ.get("COMFY_HOST", "127.0.0.1")
HOST = f"http://{COMFY_IP}:6889"
CLIENT = uuid.uuid4().hex
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_zero123")
os.makedirs(OUTDIR, exist_ok=True)

ANCHOR = os.environ.get("REF_IMG", "peach_role_v6.png")   # ComfyUI input/ 下的参考图
CKPT = "stable-zero123.ckpt"                              # models/checkpoints/ 下含 zero123 的文件


def api(path, data=None, binary=False, timeout=300):
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


def build(azimuth, prefix):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": ANCHOR}},
        "2": {"class_type": "Zero123: Image Rotate in 3D",
              "inputs": {"image": ["1", 0], "polar_angle": 0, "azimuth_angle": azimuth,
                         "scale": 1.0, "steps": 75, "batch_size": 1, "fp16": True,
                         "checkpoint": CKPT}},
        "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": prefix}},
    }


# azimuth: 0=前, 90=右, 180=后, -90=左
ANGLES = [("front", 0), ("right", 90), ("back", 180), ("left", -90)]


def main():
    all_files = []
    for name, az in ANGLES:
        print(f"[提交] {name} (azimuth={az}) ...")
        pid = submit(build(az, "z123_" + name))
        print(f"  prompt_id={pid}")
        node = wait(pid)
        files = download(node)
        all_files.extend(files)
    print("\n=== 全部完成 ===")
    for f in all_files:
        print(f)


if __name__ == "__main__":
    main()
