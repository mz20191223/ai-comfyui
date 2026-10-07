#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comfy_discover.py —— 零成本探测 HAI 上的 ComfyUI 环境（开机第一步必跑）。

只发 GET 请求，不生成任何图/视频，纯读环境信息，绝不花 GPU 钱。
目的：确认「能不能跑角色一致性视频」所需条件具备，避免盲目烧钱。

探测内容:
  1. GPU / 显存（/system_stats）
  2. 关键能力节点是否安装（AnimateDiff / VideoHelperSuite / IPAdapter / CLIPVision / VAE / LoRA）
  3. 可用模型清单（checkpoint / lora / clip_vision / ipadapter / animatediff motion / vae）

分级结论:
  - Tier1（最省，无需 IPAdapter）：AnimateDiff + VHS + SDXL + 动画模块 + VAE + Pixar LoRA
    → 用「参考图作首帧」图生视频锁角色，依赖最少
  - Tier2（+IPAdapter 锁角色增强）：Tier1 基础上再加 IPAdapter 插件 + IPAdapter 模型 + CLIPVision

用法:
  python comfy_discover.py --host http://43.155.214.240:6889
"""
import argparse
import json
import subprocess
import sys


HOST = ""


def curl_get(url, max_time=30):
    cmd = ["curl", "-sSL", "--max-time", str(max_time), "-w", "\n%{http_code}", url]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
    except Exception as e:
        return None, f"curl 异常: {e}"
    out = p.stdout
    parts = out.rsplit("\n", 1)
    body = parts[0]
    code = parts[1].strip() if len(parts) > 1 else ""
    if code != "200":
        return None, f"HTTP {code}"
    try:
        return json.loads(body), None
    except Exception as e:
        return None, f"JSON 解析失败: {e}"


def node_present(name):
    """ComfyUI /object_info/<name> 若节点存在，返回内容；否则返回 None。"""
    d, err = curl_get(f"{HOST}/object_info/{name}")
    if err or not d:
        return None
    node = d.get(name)
    if not node or not node.get("input"):
        return None
    return node


def extract_options(node, field):
    """从节点 input.required[field] 提取下拉选项列表（模型文件名）。"""
    req = node.get("input", {}).get("required", {})
    if field not in req:
        return []
    val = req[field][0]
    if isinstance(val, list) and val and isinstance(val[0], str):
        return val
    return []


def has_any(options, *keys):
    """options 里是否含任一关键词（小写匹配）。"""
    low = [o.lower() for o in options]
    return [o for o in low if any(k in o for k in keys)]


def main():
    global HOST
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://43.155.214.240:6889")
    args = ap.parse_args()
    HOST = args.host.rstrip("/")
    print("=" * 64)
    print("ComfyUI 环境探测:", HOST)
    print("=" * 64)

    # 1) 连通性 + GPU
    stats, err = curl_get(f"{HOST}/system_stats")
    if err:
        print("❌ 连不上 ComfyUI:", err)
        print("   请确认 HAI 已开机、地址正确、ComfyUI 服务已起（见 ToolBox 重启格）。")
        sys.exit(1)
    devs = stats.get("devices", [])
    if devs:
        for i, d in enumerate(devs):
            print(f"[GPU {i}] {d.get('name','?')}  "
                  f"显存 {d.get('total_memory',0)/1024/1024/1024:.1f}G  "
                  f"已用 {d.get('used_memory',0)/1024/1024/1024:.1f}G")
    else:
        print("[GPU] 未检测到设备信息")

    # 2) 关键能力节点
    print("\n--- 关键能力节点 ---")
    caps = {
        "ADE_AnimateDiffLoaderGen1": "AnimateDiff 动画模块（视频必需，ToolBox 预装）",
        "ADE_AnimateDiffSamplerWithContext": "AnimateDiff 采样器（视频推荐）",
        "VHS_VideoCombine": "视频合成输出（视频必需，需额外装 VideoHelperSuite）",
        "IPAdapterAdvanced": "角色一致性注入（Tier2 增强用，默认未装）",
        "IPAdapterModelLoader": "加载 IPAdapter 权重（Tier2 用）",
        "CLIPVisionLoader": "CLIP Vision 编码器（Tier2 用）",
        "VAELoader": "VAE 加载（SDXL VAE 必需）",
        "LoraLoader": "LoRA 加载（Pixar LoRA 必需）",
        "CheckpointLoaderSimple": "基座模型加载（必需）",
        "LoadImage": "读参考图（首帧锚定必需）",
    }
    present = {}
    for name, desc in caps.items():
        node = node_present(name)
        present[name] = node is not None
        mark = "✅" if present[name] else "❌"
        print(f"  {mark} {name:38s} {desc}")

    # 3) 模型清单
    print("\n--- 可用模型 ---")
    def scan(loader, field, label, *match_keys):
        node = node_present(loader)
        opts = extract_options(node, field) if node else []
        hit = has_any(opts, *match_keys) if match_keys else []
        if opts:
            print(f"  [{label}] 共 {len(opts)} 个"
                  + (f"，命中目标: {hit}" if hit else "（未命中目标关键词）"))
            if not match_keys:
                for o in opts[:12]:
                    print(f"      - {o}")
        else:
            print(f"  [{label}] （无 / 节点缺失）")
        return opts, hit

    ckpt_opts, sdxl_hit = scan("CheckpointLoaderSimple", "ckpt_name", "基座 checkpoint", "sdxl", "sd_xl", "xl_base")
    lora_opts, pixar_hit = scan("LoraLoader", "lora_name", "LoRA", "pixar", "canopus", "pos")
    vae_opts, vae_hit = scan("VAELoader", "vae_name", "VAE", "sdxl", "xl")
    cv_opts, cv_hit = scan("CLIPVisionLoader", "clip_name", "CLIP Vision", "clip_vision_g")
    ip_opts, ip_hit = scan("IPAdapterModelLoader", "ipadapter_file", "IPAdapter 权重", "plus-face", "sdxl")

    # 动画模块（AnimateDiff 专用目录）
    print("\n--- 动画 / 视频模块 ---")
    ad_node = node_present("ADE_AnimateDiffLoaderGen1")
    motion_opts = []
    if ad_node:
        for f in ("model_name", "motion_model"):
            motion_opts = extract_options(ad_node, f)
            if motion_opts:
                break
        if motion_opts:
            print(f"  [motion model] {len(motion_opts)} 个: {motion_opts[:8]}")
        else:
            print("  ❌ 未检测到动画模块文件（mm_sd_v15_v2.ckpt / mm_sdxl_*.safetensors 等）")
        req = ad_node.get("input", {}).get("required", {})
        print(f"  AnimateDiff 节点参数键: {list(req.keys())}")
    else:
        print("  ❌ 未检测到 AnimateDiff（ADE_AnimateDiffLoaderGen1）")

    # 4) 分级结论
    print("\n" + "=" * 64)
    print("结论（分级）")
    print("=" * 64)

    # Tier1 必需集合
    t1_nodes = ["ADE_AnimateDiffLoaderGen1", "VHS_VideoCombine",
                "VAELoader", "LoraLoader", "CheckpointLoaderSimple", "LoadImage"]
    t1_models_ok = bool(sdxl_hit) and bool(motion_opts) and bool(vae_hit) and bool(pixar_hit)
    t1_nodes_missing = [n for n in t1_nodes if not present.get(n)]
    t1_model_missing = []
    if not sdxl_hit:
        t1_model_missing.append("SDXL 基座")
    if not motion_opts:
        t1_model_missing.append("AnimateDiff 动画模块")
    if not vae_hit:
        t1_model_missing.append("SDXL VAE")
    if not pixar_hit:
        t1_model_missing.append("Pixar LoRA")

    print("\n【Tier1 · 最省方案：参考图作首帧锁角色（无需 IPAdapter）】")
    if t1_nodes_missing:
        print("  缺节点:", t1_nodes_missing)
    else:
        print("  节点 ✅")
    if t1_model_missing:
        print("  缺模型:", t1_model_missing)
    else:
        print("  模型 ✅")
    if not t1_nodes_missing and not t1_model_missing:
        print("  ✅ Tier1 就绪：可用 gen_video_clip.py --no-ipadapter 跑首帧锚定测试片")
    else:
        print("  → 先补齐再跑（见 PLAN.md「开机补齐清单」）")

    print("\n【Tier2 · 增强：+IPAdapter 强锁角色】")
    if present.get("IPAdapterAdvanced") and cv_hit and ip_hit:
        print("  ✅ IPAdapter 插件 + 模型 + CLIPVision 齐全，可启用 --ip-weight")
    else:
        miss = []
        if not present.get("IPAdapterAdvanced"):
            miss.append("IPAdapter 插件(ComfyUI-IPAdapter-Plus)")
        if not cv_hit:
            miss.append("clip_vision_g 模型")
        if not ip_hit:
            miss.append("ip-adapter-plus-face_sdxl 模型")
        print("  当前缺:", miss if miss else "无")
        print("  → 仅当 Tier1 首帧锚定仍漂移时才需要装（多 1 插件 + ~3.3G 模型）")

    print("\n建议第一步：先用 Tier1 跑【1 段测试片】验证一致性，")
    print("满意再批量；不满意再升级 Tier2，避免浪费额度。")


if __name__ == "__main__":
    main()
