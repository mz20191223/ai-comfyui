#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开机第一步：探测 ComfyUI 已装节点，核对云端管线需要的节点/能力是否齐全。

用法:
  python check_cloud_nodes.py --host http://HOST:6889

它会拉取 /object_info（所有节点类名），按"候选名"模糊匹配我们依赖的节点，
输出 已装 / 缺失 两栏，并给出缺失项的安装提示。
"""
import sys, os, json, subprocess, argparse


def curl_get(url, max_time=60):
    cmd = ["curl", "-sSL", "--max-time", str(max_time), url]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
        return p.stdout
    except Exception as e:
        print("  [curl 异常]", e); return ""


# 类别 -> 候选节点类名（只要出现任意一个即视为具备该能力）
EXPECTED = {
    "LTX 2.3 视频模型": [
        "LTXVModelLoader", "LTXVideo", "LTXVLoader", "LTXVConditioning",
        "LTXVSampler", "LTXVDecode", "LTXVTextEmbedInterpolator",
    ],
    "Licon-MSR 多参考": [
        "LiconMSR", "MSR", "MSRReference", "MSRConditioning", "ReferenceVideo",
    ],
    "Qwen-Image-Edit-2511": [
        "QwenImageEdit", "QwenImageEditLoader", "QwenImageEditModel",
        "QwenImageEditV2", "QwenImageEditCondition",
    ],
    "Gemma 文本编码器": [
        "LTXVTextEmbedInterpolator", "Gemma", "Qwen2VL", "LTXVTextEncode",
    ],
    "VAE (LTX)": [
        "LTXVVAELoader", "VAELoader",
    ],
    "视频拼接/输出": [
        "VHS_VideoCombine", "VideoCombine", "SaveVideo",
    ],
    "图像保存": [
        "SaveImage", "ImageSave",
    ],
    "参考图加载(多图)": [
        "LoadImage", "ImageLoader", "LoadImagesFromFolder",
    ],
}

GITHUB_HINTS = {
    "LTX 2.3 视频模型": "ComfyUI-LTXVideo 或 Kijai/ComfyUI-LTXVideo (需 ComfyUI v0.16+)",
    "Licon-MSR 多参考": "ComfyUI-Licon-MSR (+ MSR IC-LoRA V2 权重)",
    "Qwen-Image-Edit-2511": "ComfyUI-Qwen-Image-Edit (或对应 GGUF 加载节点)",
    "Gemma 文本编码器": "随 LTX 节点包提供 (Gemma-3-12B GGUF)",
    "VAE (LTX)": "taeltx2_3 VAE 权重",
    "视频拼接/输出": "ComfyUI-VideoHelperSuite",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    args = ap.parse_args()
    host = args.host.rstrip("/")

    print("==> 探测", host, "/object_info ...")
    raw = curl_get(host + "/object_info", max_time=120)
    if not raw:
        print("!! 无法获取 object_info，确认地址/端口正确、ComfyUI 已启动")
        sys.exit(1)
    try:
        info = json.loads(raw)
    except Exception:
        print("!! object_info 不是合法 JSON（可能返回了 HTML 错误页）")
        print(raw[:400])
        sys.exit(1)

    all_nodes = list(info.keys())
    print("==> 共探测到 %d 个节点类\n" % len(all_nodes))

    missing = []
    for cat, cands in EXPECTED.items():
        hits = [c for c in cands if any(c.lower() in n.lower() for n in all_nodes)]
        if hits:
            print("  [OK]  %-22s -> %s" % (cat, ", ".join(sorted(set(hits))[:4])))
        else:
            print("  [缺失] %-22s (候选: %s)" % (cat, ", ".join(cands[:3])))
            missing.append(cat)

    print("\n==> 汇总")
    if not missing:
        print("  所有依赖节点已就绪，可直接进入工作流组装。")
    else:
        print("  缺失 %d 类，开机后需先安装：" % len(missing))
        for m in missing:
            print("   - %s : %s" % (m, GITHUB_HINTS.get(m, "见上方候选节点说明")))
        print("\n提示：节点装好后需重启 ComfyUI 再跑一次本脚本确认。")


if __name__ == "__main__":
    main()
