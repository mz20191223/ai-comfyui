#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hai_c1.py —— 本机侧 C1 一键出 9 宫格（用户开 HAI 后，给地址就跑）。

前置: HAI 侧已跑 hai_c1_setup.sh（clone 插件 + 下权重 + 重启 ComfyUI）。
本脚本只走 ComfyUI HTTP API：
  - 连 /system_stats 做 1 秒连通检测（不烧 GPU）
  - 上传 hedgehog_hero.png（小图，HTTP multipart）
  - 读 workflows/i2mv_sdxl_ldm.json，自动注入：
        * LoadImage 参考图文件名 = 上传返回名
        * DiffusersMVSampler prompt/neg = 刺猬英文描述（覆盖原 anime girl）
        * 若无 SaveImage 节点则程序化加一个（否则下载不到图）
  - POST /prompt 提交 C1（这时才开始烧 GPU）
  - 轮询 /history 直到完成
  - 下载 9 宫格到 c1_output/

用法:
  python hai_c1.py --host http://<HAI_IP>:6889
"""
import sys, os, json, time, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "hedgehog_hero.png")
WF_TPL = os.path.join(HERE, "workflows", "i2mv_sdxl_ldm.json")
OUT = os.path.join(HERE, "c1_output")

# 刺猬英文 prompt（DiffusersMVSampler 吃英文；覆盖官方模板的 anime girl）
C1_PROMPT = ("A cute chibi hedgehog character, round fluffy body, big sparkly eyes, "
             "soft brown fur, Pixar Disney 3D render style, standing pose, collectible figurine")
C1_NEG = "watermark, ugly, deformed, noisy, blurry, low contrast, extra limbs, bad anatomy"


def curl(args, max_time=60, retries=3):
    for _ in range(1, retries + 1):
        cmd = ["curl", "-sSL", "--max-time", str(max_time), "-w", "\n%{http_code}"] + args
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
            out = p.stdout
            parts = out.rsplit("\n", 1)
            return (parts[1].strip() if len(parts) > 1 else ""), parts[0]
        except Exception as e:
            print(f"  [curl 异常 {e}]")
    return "000", ""


def curl_download(url, dest, max_time=120):
    cmd = ["curl", "-sSL", "--max-time", str(max_time), "-o", dest, url]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
    return p.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0


def upload_image(host, path):
    cmd = ["curl", "-sSL", "-F", f"image=@{path}", host + "/upload/image"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(p.stdout)["name"]
    except Exception:
        print("!! 上传参考图失败:", p.stdout[:500])
        sys.exit(1)


def build_c1_prompt(ref_name, num_views=6, seed=21):
    """确定性构造 C1 九宫格的 API 格式工作流（/prompt 接口用）。

    为什么不用 UI 格式转换：实测 HAI 装的 MV-Adapter 节点版本与官方模板不一致
    （如 DiffusersMVSampler 没了 scheduler 参数、LdmVaeLoader required 顺序不同、
    LoadImage image 是 image_upload 复合类型），索引对齐极脆。这里直接按
    object_info 真实定义 + 固定拓扑手工构造，每个输入名精确匹配，版本无关。
    adapter_path 指向 HAI 上已下好的本地权重，避免重复下载 3.4G。
    """
    ADAPTER_DIR = "/root/ComfyUI/models/mvadapter"
    return {
        "1": {"class_type": "LdmPipelineLoader", "inputs": {
            "ckpt_name": "sd_xl_base_1.0.safetensors",
            "pipeline_name": "MVAdapterI2MVSDXLPipeline"}},
        "2": {"class_type": "DiffusersMVSchedulerLoader", "inputs": {
            "pipeline": ["1", 0],
            "scheduler_name": "DDPM",
            "shift_snr": True,
            "shift_mode": "interpolated",
            "shift_scale": 8.0}},
        "3": {"class_type": "LdmVaeLoader", "inputs": {
            "vae_name": "sdxl_vae.safetensors",
            "upcast_fp32": True}},
        "4": {"class_type": "DiffusersMVModelMakeup", "inputs": {
            "pipeline": ["1", 0],
            "scheduler": ["2", 0],
            "autoencoder": ["3", 0],
            "load_mvadapter": True,
            "adapter_path": ADAPTER_DIR,
            "adapter_name": "mvadapter_i2mv_sdxl.safetensors",
            "num_views": num_views}},
        "6": {"class_type": "DiffusersMVSampler", "inputs": {
            "pipeline": ["4", 0],
            "num_views": num_views,
            "prompt": C1_PROMPT,
            "negative_prompt": C1_NEG,
            "width": 768,
            "height": 768,
            "steps": 50,
            "cfg": 3,
            "seed": seed,
            "reference_image": ["8", 0]}},
        "7": {"class_type": "LoadImage", "inputs": {"image": ref_name}},
        "8": {"class_type": "ImagePreprocessor", "inputs": {
            "remove_bg_fn": ["9", 0],
            "image": ["7", 0],
            "height": 768,
            "width": 768}},
        "9": {"class_type": "BiRefNet", "inputs": {"ckpt_name": "ZhengPeng7/BiRefNet"}},
        "10": {"class_type": "PreviewImage", "inputs": {"images": ["8", 0]}},
        "11": {"class_type": "PreviewImage", "inputs": {"images": ["6", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "C1_9grid"}},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="HAI 上 ComfyUI 地址，如 http://1.2.3.4:6889")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    HOST = a.host.rstrip("/")
    print("==> ComfyUI:", HOST)

    if not os.path.exists(REF):
        print("!! 找不到参考图", REF)
        sys.exit(1)

    # 1) 连通检测（1 秒，不烧 GPU）
    code, _ = curl([HOST + "/system_stats"], max_time=20)
    if code != "200":
        print("!! 连不上 (HTTP %s)，确认 HAI 已开、地址正确、ComfyUI 已起" % code)
        sys.exit(1)
    print("==> 连通 OK")

    # 2) 上传参考图
    print("==> 上传参考图...")
    ref_name = upload_image(HOST, REF)
    print("   上传为:", ref_name)

    # 3) 确定性构造 C1 API 工作流（版本无关，输入名精确匹配）
    print("==> 构造 C1 工作流 (num_views=%d)..." % 6)
    api_prompt = build_c1_prompt(ref_name, num_views=6, seed=21)
    payload = json.dumps({"prompt": api_prompt, "client_id": "wb_c1_%d" % int(time.time())}).encode("utf-8")
    tmp = os.path.join(HERE, "c1_payload.tmp")
    with open(tmp, "wb") as f:
        f.write(payload)

    # 4) 提交（开始烧 GPU）
    code, body = curl(["-X", "POST", "-H", "Content-Type: application/json",
                       "--data-binary", "@" + tmp, HOST + "/prompt"], max_time=60)
    try:
        os.remove(tmp)
    except OSError:
        pass
    print("POST /prompt ->", code)
    if code != "200":
        print(body[:1500])
        print("!! 提交失败")
        sys.exit(1)
    pid = json.loads(body)["prompt_id"]
    print("prompt_id =", pid)

    # 5) 轮询
    start = time.time()
    from urllib.parse import quote
    while time.time() - start < a.timeout:
        code, body = curl([HOST + "/history/" + pid], max_time=20)
        if code == "200" and body:
            try:
                hist = json.loads(body)
            except Exception:
                time.sleep(5)
                continue
            if pid in hist:
                e = hist[pid]
                for m in e.get("status", {}).get("messages", []):
                    if m[0] == "execution_error":
                        print("\n!!! 执行错误:")
                        print(json.dumps(m[1], ensure_ascii=False, indent=2))
                        sys.exit(2)
                outs = e.get("outputs", {})
                imgs = []
                for nid, o in outs.items():
                    for im in o.get("images", []):
                        imgs.append((nid, im.get("filename"), im.get("subfolder", ""), im.get("type", "output")))
                if not imgs:
                    print("!! 无输出图像（应已自动加 SaveImage，若仍为空检查插件是否加载）")
                    sys.exit(3)
                os.makedirs(a.out, exist_ok=True)
                print("==> 完成, 图像数", len(imgs), "下载到", a.out)
                for nid, fn, sub, typ in imgs:
                    url = "%s/view?filename=%s&subfolder=%s&type=%s" % (HOST, quote(fn), quote(sub), quote(typ))
                    dest = os.path.join(a.out, os.path.basename(fn))
                    ok = curl_download(url, dest)
                    print("  [%s] %s -> %s %s" % (nid, fn, dest, "OK" if ok else "FAIL"))
                print("==> 全部完成")
                sys.exit(0)
        time.sleep(5)
    print("!! 超时未完成 (%ds)" % a.timeout)


if __name__ == "__main__":
    main()
