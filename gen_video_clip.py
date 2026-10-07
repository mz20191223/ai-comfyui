#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_video_clip.py —— C2 版：用 HAI ComfyUI 生成「角色一致性」视频片段。

本地（Agnes）负责: 分镜 JSON + 角色参考图(hero) + 6 张角度图(C1 九宫格)
本脚本负责:        把参考图作「首帧锚定」+ IPAdapter(plus 全身版)弱锁身份
                  + AnimateDiff 生成动作 → 下载 mp4

相较旧版的关键修正（C2 方案要求）:
  1. **首帧锚定**: 参考图经 VAEEncode → RepeatLatentBatch 成多帧 → KSampler denoise≈0.6
     让角色在视频起点被「钉死」，不依赖 IPAdapter 单独锁死（非人类 IPAdapter 锁不住已是教训）
  2. **IPAdapter 优先 plus 全身版**: 自动从 ipadapter_file 列表挑 `ip-adapter-plus_sdxl_vit-h`
     （非 plus-face；face 版只抓脸，刺猬无人类脸→失效）
  3. **弱锁**: IP 权重默认 0.7（区间 0.6~0.85），留动作空间，不 0.95 否则僵死
  4. **多视图参考**: --refs 可传多张角度图，首帧用第 1 张；验证帧间一致后再上多图增强

设计原则（稳，不浪费钱）:
  - 开机后先跑 comfy_discover.py 确认环境（尤其 IPAdapter_plus 插件 / AnimateDiff 模块是否就绪）
  - 本脚本提交前会先「探测可用节点/模型名」，按真实名称建图
  - 首次务必只跑 1 段测试片（--test），确认角色一致再批量

用法:
  # 1 段测试片（先验证角色一致性）—— 用 hero 作首帧 + IPAdapter 参考
  python gen_video_clip.py --host http://<HAI_IP>:6889 \
      --ref hedgehog_hero.png \
      --prompt "小刺猬轻轻眨眼睛，正面，皮克斯3D风格" \
      --out test_clip.mp4 --test

  # 用 6 张角度图：首帧取正面那张，IPAdapter 参考也用它（先验证单图弱锁）
  python gen_video_clip.py --host http://<HAI_IP>:6889 \
      --refs c1_output/C1_9grid_00001_.png c1_output/C1_9grid_00002_.png ... \
      --out test_clip.mp4 --test
"""
import argparse
import json
import os
import subprocess
import sys
import time


def curl(args, max_time=60, retries=3):
    for attempt in range(1, retries + 1):
        cmd = ["curl", "-sSL", "--max-time", str(max_time), "-w", "\n%{http_code}"] + args
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 20)
            out = p.stdout
            parts = out.rsplit("\n", 1)
            return parts[1].strip() if len(parts) > 1 else "", parts[0]
        except Exception as e:
            print(f"  [curl 异常 {e}, 第{attempt}次]")
    return "000", ""


def http_get_json(url, max_time=30):
    code, body = curl(["-X", "GET", url], max_time=max_time)
    if code != "200" or not body:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


def upload_image(host, path):
    """把本地参考图传到 ComfyUI input 目录，返回服务器文件名。"""
    fname = os.path.basename(path)
    code, body = curl(["-X", "POST", "-F", f"image=@{path}",
                       "-F", "overwrite=true", f"{host}/upload/image"], max_time=60)
    if code == "200" and body:
        try:
            return json.loads(body).get("name", fname)
        except Exception:
            pass
    # 兜底：直接用原文件名（若已手工放好）
    return fname


def discover(host):
    """探测关键节点与模型名，返回建图所需信息（自适应 HAI 真实安装）。"""
    info = {}

    # ---- AnimateDiff 加载器（取第一个存在的）----
    for cand in ["ADE_AnimateDiffLoaderGen1", "AnimateDiffLoaderWithModelSpec",
                 "AnimateDiffLoader", "ADE_AnimateDiffLoaderGen2"]:
        node = http_get_json(f"{host}/object_info/{cand}")
        if node and node.get(cand, {}).get("input"):
            info["anim"] = cand
            req = node[cand]["input"]["required"]
            for f in ("model_name", "motion_model"):
                if f in req and isinstance(req[f][0], list):
                    info["motion_models"] = req[f][0]
                    break
            break

    # ---- 视频合成 ----
    for cand in ["VHS_VideoCombine", "VideoCombine"]:
        node = http_get_json(f"{host}/object_info/{cand}")
        if node and node.get(cand, {}).get("input"):
            info["video"] = cand
            break

    # ---- 首帧锚定所需：RepeatLatentBatch（ComfyUI 原生）----
    rb = http_get_json(f"{host}/object_info/RepeatLatentBatch")
    if rb and rb.get("RepeatLatentBatch", {}).get("input"):
        info["repeat"] = "RepeatLatentBatch"
    else:
        info["repeat"] = None

    # ---- checkpoint / lora / clip_vision 取第一个可用文件 ----
    def first_option(node_name, field):
        node = http_get_json(f"{host}/object_info/{node_name}")
        if not node or not node.get(node_name, {}).get("input"):
            return None
        req = node[node_name]["input"]["required"]
        if field in req and isinstance(req[field][0], list) and req[field][0]:
            return req[field][0][0]
        return None

    info["ckpt"] = first_option("CheckpointLoaderSimple", "ckpt_name")
    info["lora"] = first_option("LoraLoader", "lora_name")
    info["clip"] = first_option("CLIPVisionLoader", "clip_name")

    # ---- IPAdapter：优先 plus 全身版（非 face）----
    ipa_node = http_get_json(f"{host}/object_info/IPAdapterModelLoader")
    info["ipadapter"] = None
    if ipa_node and ipa_node.get("IPAdapterModelLoader", {}).get("input"):
        req = ipa_node["IPAdapterModelLoader"]["input"]["required"]
        opts = req.get("ipadapter_file", [[]])[0]
        if isinstance(opts, list) and opts:
            # 优先 ip-adapter-plus_sdxl_vit-h（全身版，对非人类角色更合适）
            for o in opts:
                if "plus_sdxl" in o and "face" not in o:
                    info["ipadapter"] = o
                    break
            if not info["ipadapter"]:
                info["ipadapter"] = opts[0]
    return info


def build_workflow(ref_name, pos, neg, info, frames=24, fps=12,
                   ip_weight=0.7, lora_strength=0.85, denoise=0.6):
    """构造 C2 视频工作流（API 格式）。

    拓扑:
      LoadImage(首帧) → VAEEncode → RepeatLatentBatch(frames) → KSampler(denoise=0.6, 首帧锚定)
      Checkpoint → Lora → IPAdapterAdvanced(plus全身版, image=首帧图, 弱锁) → AnimateDiff → KSampler.model
      KSampler → VAEDecode → VHS_VideoCombine
    """
    ckpt, lora, ipa, clip = info["ckpt"], info["lora"], info["ipadapter"], info["clip"]
    rep = info.get("repeat") or "RepeatLatentBatch"
    wf = {}

    wf["1"] = {"class_type": "CheckpointLoaderSimple",
               "inputs": {"ckpt_name": ckpt}, "_meta": {"title": "基座"}}
    wf["4"] = {"class_type": "LoraLoader",
               "inputs": {"model": ["1", 0], "clip": ["1", 1],
                          "lora_name": lora,
                          "strength_model": lora_strength,
                          "strength_clip": lora_strength},
               "_meta": {"title": "皮克斯 LoRA"}}

    # 首帧锚定链路
    wf["11"] = {"class_type": "LoadImage",
                "inputs": {"image": ref_name}, "_meta": {"title": "首帧图(锚定)"}}
    wf["91"] = {"class_type": "VAEEncode",
                "inputs": {"pixels": ["11", 0], "vae": ["1", 2]},
                "_meta": {"title": "首帧 VAE 编码"}}
    # RepeatLatentBatch: amount = 额外复制次数 → 总帧 = 1 + amount
    wf["93"] = {"class_type": rep,
                "inputs": {"samples": ["91", 0], "amount": max(frames - 1, 0)},
                "_meta": {"title": "复制成多帧"}}
    wf["92"] = {"class_type": "CLIPVisionLoader",
                "inputs": {"clip_name": clip}, "_meta": {"title": "CLIP Vision"}}
    wf["90"] = {"class_type": "IPAdapterModelLoader",
                "inputs": {"ipadapter_file": ipa}, "_meta": {"title": "IPAdapter(plus全身版)"}}
    wf["10"] = {"class_type": "IPAdapterAdvanced",
                "inputs": {"model": ["4", 0], "ipadapter": ["90", 0],
                           "image": ["11", 0], "clip_vision": ["92", 0],
                           "weight": ip_weight, "weight_type": "linear",
                           "combine_embeds": "concat", "start_at": 0.0,
                           "end_at": 1.0, "embeds_scaling": "V only"},
                "_meta": {"title": "IPAdapter 弱锁身份"}}

    # AnimateDiff 应用到模型
    anim = info.get("anim")
    if anim:
        mname = (info.get("motion_models") or [None])[0]
        wf["95"] = {"class_type": anim,
                    "inputs": {"model": ["10", 0], "model_name": mname,
                               "beta_schedule": "autoselect"},
                    "_meta": {"title": "AnimateDiff 动作"}}
        model_out = ["95", 0]
    else:
        model_out = ["10", 0]

    wf["6"] = {"class_type": "CLIPTextEncode",
               "inputs": {"text": pos, "clip": ["4", 1]}, "_meta": {"title": "正"}}
    wf["7"] = {"class_type": "CLIPTextEncode",
               "inputs": {"text": neg, "clip": ["4", 1]}, "_meta": {"title": "负"}}
    wf["3"] = {"class_type": "KSampler",
               "inputs": {"model": model_out, "positive": ["6", 0],
                          "negative": ["7", 0], "latent_image": ["93", 0],
                          "seed": int(time.time() * 1000) % (2**32),
                          "steps": 25, "cfg": 7.0,
                          "sampler_name": "dpmpp_2m", "scheduler": "karras",
                          "denoise": denoise}, "_meta": {"title": "采样(首帧锚定)"}}
    wf["8"] = {"class_type": "VAEDecode",
               "inputs": {"samples": ["3", 0], "vae": ["1", 2]},
               "_meta": {"title": "VAE 解码"}}
    vc = info.get("video", "VHS_VideoCombine")
    wf["9"] = {"class_type": vc,
               "inputs": {"images": ["8", 0], "frame_rate": fps,
                          "loop_count": 0, "filename_prefix": "clip",
                          "format": "video/h264-mp4", "pingpong": False,
                          "save_output": True},
               "_meta": {"title": "合成视频"}}
    return wf


def submit_and_wait(host, wf, timeout=900):
    payload = json.dumps({"prompt": wf, "client_id": "wb_%d" % int(time.time())})
    tmp = "_clip_payload.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
    code, body = curl(["-X", "POST", "-H", "Content-Type: application/json",
                       "--data-binary", "@" + tmp, f"{host}/prompt"], max_time=60)
    try:
        os.remove(tmp)
    except OSError:
        pass
    if code != "200":
        print("!! 提交失败 HTTP", code, body[:500])
        return None, None
    pid = json.loads(body).get("prompt_id")
    print("prompt_id =", pid)
    start = time.time()
    while time.time() - start < timeout:
        code, body = curl(["-X", "GET", f"{host}/history/{pid}"], max_time=20)
        if code == "200" and body:
            hist = json.loads(body)
            if pid in hist:
                entry = hist[pid]
                for m in entry.get("status", {}).get("messages", []):
                    if m[0] == "execution_error":
                        print("!!! 执行错误:", json.dumps(m[1], ensure_ascii=False)[:800])
                        return pid, None
                outs = entry.get("outputs", {})
                for nid, o in outs.items():
                    for v in o.get("videos", []):
                        return pid, (v.get("filename"), v.get("subfolder", ""),
                                     v.get("type", "output"))
                    for im in o.get("images", []):
                        if im.get("filename", "").endswith((".mp4", ".webm")):
                            return pid, (im.get("filename"), im.get("subfolder", ""),
                                         v.get("type", "output"))
                return pid, None
        time.sleep(5)
    print("!! 超时")
    return pid, None


def download(host, vinfo, dest):
    fn, sub, typ = vinfo
    from urllib.parse import quote
    url = f"{host}/view?filename={quote(fn)}&subfolder={quote(sub)}&type={quote(typ)}"
    code, _ = curl(["-X", "GET", "-o", dest, url], max_time=180)
    if code == "200" and os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://43.155.214.240:6889")
    ap.add_argument("--ref", help="单张参考图(作首帧+IPAdapter参考)；与 --refs 互斥，--refs 优先")
    ap.add_argument("--refs", nargs="+", help="多张角度图；第1张作首帧，IPAdapter 参考也用第1张")
    ap.add_argument("--prompt", required=True, help="该镜正向提示词")
    ap.add_argument("--neg", default="ugly, deformed, extra ears, four ears, pig nose, blurry, lowres, watermark, text, multiple animals")
    ap.add_argument("--out", default="clip.mp4")
    ap.add_argument("--frames", type=int, default=24, help="视频总帧数(测试片建议16~32)")
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--ip-weight", type=float, default=0.7, help="IPAdapter 权重 0.6~0.85 弱锁")
    ap.add_argument("--denoise", type=float, default=0.6, help="首帧锚定强度，0.5~0.7")
    ap.add_argument("--test", action="store_true", help="提醒先跑测试片（实际操作同）")
    a = ap.parse_args()
    host = a.host.rstrip("/")

    # 选参考图：--refs 优先，取第 1 张
    if a.refs:
        ref_local = a.refs[0]
        print(f"多视图模式: 用 {len(a.refs)} 张, 首帧={os.path.basename(ref_local)}")
    elif a.ref:
        ref_local = a.ref
    else:
        print("!! 必须给 --ref 或 --refs")
        sys.exit(1)

    info = discover(host)
    missing = [k for k in ("anim", "video", "ckpt", "lora", "ipadapter", "clip", "repeat")
               if not info.get(k)]
    if missing:
        print("❌ 环境缺必需项:", missing)
        print("   → C2 需先补: IPAdapter_plus 插件 + ip-adapter-plus_sdxl_vit-h + clip_vision_g + AnimateDiff 模块, 再重启")
        sys.exit(1)
    print(f"环境: ckpt={info['ckpt']} lora={info['lora']} "
          f"ipadapter={info['ipadapter']} clip={info['clip']} "
          f"anim={info['anim']} repeat={info['repeat']}")

    ref_name = upload_image(host, ref_local)
    print("参考图已上传:", ref_name)
    wf = build_workflow(ref_name, a.prompt, a.neg, info,
                        frames=a.frames, fps=a.fps,
                        ip_weight=a.ip_weight, denoise=a.denoise)
    print(f"提交视频（{a.frames}帧 @ {a.fps}fps, IP权重 {a.ip_weight}, denoise {a.denoise}）...")
    pid, vinfo = submit_and_wait(host, wf)
    if not vinfo:
        print("❌ 生成失败，看上面错误")
        sys.exit(2)
    ok = download(host, vinfo, a.out)
    if ok:
        print(f"✅ 视频已下载: {os.path.abspath(a.out)}")
    else:
        print("❌ 下载失败")


if __name__ == "__main__":
    main()
