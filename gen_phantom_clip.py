#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_phantom_clip.py —— Phantom(Wan2.1 1.3B) 视频提交脚本（替代已弃用的 AnimateDiff+IPAdapter 路线）。

为什么换 Phantom（C2 失败复盘）：
  C2 用 AnimateDiff+IPAdapter(plus 全身版)+首帧锚定，非人类角色(刺猬)锁不住——
  帧间 MSE 仅 22~65（内部一致）但输出根本不是参考刺猬（vs hero MSE~890），几乎无运动。
  根因：IP-Adapter / AnimateDiff 对「非人类角色 + 任意背景」身份保持弱（ConsiStory 论文点名）。
  → 改走零样本 S2V 的 Phantom（字节，Wan2.1 基座）：原生多参考图(≤4)做 subject-consistent
    视频生成，非人类角色友好，T4(15.6G) 量化后约 4~8GB 可吃。

本脚本特性：
  - **自探测**：开机后先 GET /object_info 探测真实节点名/模型文件名，按实际名称建图，
    不写死（WanVideoWrapper 节点名各版本略有差异，开机即用真实值）。
  - **多参考图**：--refs 可传 1~4 张（hero + 角度图），全部编码成 phantom latent 注入。
  - **--dry-run**：只打印探测结果与将要提交的工作流 JSON，不出片、不花 GPU，先核对。
  - 复用 gen_video_clip.py 的 curl / upload / submit / download 范式。

拓扑（来自 ComfyUI-WanVideoWrapper + Phantom 官方工作流）：
  WanVideoModelLoader(Phantom-Wan) + WanVideoVAELoader + LoadWanVideoT5TextEncoder(umt5 fp8)
    → WanVideoTextEncode(pos,neg) → text_embeds
  每张参考图: LoadImage → WanVideoEncode(image→latent) → phantom_latent_1..4
    → WanVideoPhantomEmbeds → image_embeds
  WanVideoEmptyLatent(w,h,frames) → latent
    → WanVideoSampler(model, text_embeds, latent, image_embeds=phantom) → samples
    → WanVideoDecode → VHS_VideoCombine → mp4

用法：
  # 先 dry-run 核对环境（不花 GPU）
  python gen_phantom_clip.py --host http://<HAI_IP>:6889 \
      --refs hedgehog_hero_cute2.png c1_output/C1_9grid_00001_.png \
      --prompt "小刺猬在阳光下的草地上快乐打滚" --out test.mp4 --dry-run

  # 出片（480p，33 帧 @16fps，T4 友好）
  python gen_phantom_clip.py --host http://<HAI_IP>:6889 \
      --refs hedgehog_hero_cute2.png c1_output/C1_9grid_00001_.png c1_output/C1_9grid_00002_.png \
      --prompt "小刺猬脚一滑扑通掉进小河里，溅起水花" --out shot_river.mp4
"""
import argparse
import json
import os
import subprocess
import sys
import time


# ---------------------------------------------------------------------------
# 基础 HTTP/curl 工具（与 gen_video_clip.py 同范式，本机连 ComfyUI 用 curl 更稳）
# ---------------------------------------------------------------------------
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


def get_node_info(host, name):
    """返回 object_info[name] 原始结构（含 input.required/optional + output），失败返回 None。"""
    return http_get_json(f"{host}/object_info/{name}")


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
    return fname


# ---------------------------------------------------------------------------
# 探测：自适应 HAI 真实安装的节点名与模型文件名
# ---------------------------------------------------------------------------
ROLE_CANDIDATES = {
    "model_loader":        ["WanVideoModelLoader"],
    "vae_loader":          ["WanVideoVAELoader"],
    "text_encoder_loader": ["LoadWanVideoT5TextEncoder"],
    "text_encode":         ["WanVideoTextEncode"],
    "image_encode":        ["WanVideoEncode", "WanVideoImageToVideoEncode"],
    "phantom":             ["WanVideoPhantomEmbeds"],
    "empty_latent":        ["WanVideoEmptyLatent", "EmptyLatentImage"],
    "sampler":             ["WanVideoSampler"],
    "decode":              ["WanVideoDecode"],
    "video":               ["VHS_VideoCombine", "VideoCombine"],
}


def merge_inputs(node_info):
    """合并 required + optional 输入字段，返回 {field: [options_or_type, ...]}。"""
    inp = node_info.get("input", {})
    merged = {}
    for sect in ("required", "optional"):
        for f, v in (inp.get(sect) or {}).items():
            merged[f] = v
    return merged


def discover(host):
    """探测关键节点与模型名。返回建图所需信息（自适应 HAI 真实安装）。"""
    info = {"schema": {}, "outputs": {}, "files": {}}

    for role, cands in ROLE_CANDIDATES.items():
        for c in cands:
            node = get_node_info(host, c)
            if node and node.get(c, {}).get("input"):
                info[role] = c
                info["schema"][c] = merge_inputs(node[c])
                outs = node[c].get("output") or node[c].get("output_name") or []
                info["outputs"][c] = outs
                break
        else:
            info[role] = None

    # 模型文件名选择（从探测到的下拉选项里挑）
    def pick(schema, field, *keywords):
        opts = schema.get(field, [[]])[0]
        if isinstance(opts, list) and opts:
            for k in keywords:
                for o in opts:
                    if k.lower() in o.lower():
                        return o
            return opts[0]
        return None

    if info.get("model_loader"):
        s = info["schema"][info["model_loader"]]
        info["files"]["model"] = pick(s, "model", "phantom")
    if info.get("vae_loader"):
        s = info["schema"][info["vae_loader"]]
        info["files"]["vae"] = pick(s, "vae_name", "vae", "wan")
    if info.get("text_encoder_loader"):
        s = info["schema"][info["text_encoder_loader"]]
        info["files"]["text_encoder"] = pick(s, "textencoder", "text_encoder", "umt5")
    return info


def field_of(schema, *candidates):
    """在 schema 里找第一个存在的字段名（兼容不同版本命名）。"""
    for c in candidates:
        if c in schema:
            return c
    return None


# ---------------------------------------------------------------------------
# 构造 Phantom 工作流（API 格式，schema 驱动，自适应字段名）
# ---------------------------------------------------------------------------
def build_workflow(ref_names, pos, neg, info,
                   width=832, height=480, frames=33, fps=16,
                   steps=30, cfg=5.0, phantom_cfg=5.0, seed=None):
    s = info["schema"]
    wf = {}

    # 1) 主模型
    ml = info["model_loader"]
    wf["1"] = {"class_type": ml,
               "inputs": {field_of(s[ml], "model"): info["files"]["model"]},
               "_meta": {"title": "Phantom-Wan-1.3B"}}

    # 2) VAE
    vl = info["vae_loader"]
    wf["2"] = {"class_type": vl,
               "inputs": {field_of(s[vl], "vae_name", "vae"): info["files"]["vae"]},
               "_meta": {"title": "wan_2.1_vae"}}

    # 3) 文本编码器（umt5 fp8）
    te_out = None
    tel = info.get("text_encoder_loader")
    if tel:
        wf["3"] = {"class_type": tel,
                   "inputs": {field_of(s[tel], "textencoder", "text_encoder"): info["files"]["text_encoder"]},
                   "_meta": {"title": "umt5_xxl_fp8"}}
        te_out = ["3", 0]

    # 4) 文本编码（正 + 负）
    te = info["text_encode"]
    te_in = {field_of(s[te], "model"): ["1", 0],
             field_of(s[te], "positive"): pos,
             field_of(s[te], "negative"): neg}
    if te_out:
        te_in[field_of(s[te], "text_encoder", "textencoder", "clip")] = te_out
    wf["4"] = {"class_type": te, "inputs": te_in, "_meta": {"title": "文本条件"}}

    # 文本编码输出：若有两个输出(positive/negative)分别接，否则同一输出接两者
    te_outs = info["outputs"].get(te, [])
    if len(te_outs) >= 2:
        pos_out, neg_out = ["4", 0], ["4", 1]
    else:
        pos_out = neg_out = ["4", 0]

    # 5) 参考图 → latent（每张一张 LoadImage + 一个 encode）
    ie = info["image_encode"]
    latent_ids = []
    for i, rn in enumerate(ref_names):
        rid = 10 + i
        eid = 20 + i
        wf[str(rid)] = {"class_type": "LoadImage",
                        "inputs": {"image": rn}, "_meta": {"title": f"参考图{i+1}"}}
        ie_in = {field_of(s[ie], "image"): [str(rid), 0],
                 field_of(s[ie], "vae", "vae_name"): ["2", 0]}
        mf = field_of(s[ie], "model")
        if mf:
            ie_in[mf] = ["1", 0]
        wf[str(eid)] = {"class_type": ie, "inputs": ie_in,
                        "_meta": {"title": f"参考图{i+1}编码"}}
        latent_ids.append([str(eid), 0])

    # 6) Phantom embeds（最多 4 张参考）
    ph = info["phantom"]
    ps = s[ph]
    ph_in = {field_of(ps, "num_frames", "frames"): frames,
             field_of(ps, "phantom_cfg_scale", "cfg_scale"): phantom_cfg}
    for f, d in (("phantom_start_percent", "start_percent"), ("start_percent",),
                 ("phantom_end_percent", "end_percent"), ("end_percent",)):
        ff = field_of(ps, f, *d)
        if ff:
            ph_in[ff] = 0.0 if "start" in ff else 1.0
    for i in range(4):
        fld = f"phantom_latent_{i+1}"
        if fld in ps:
            ph_in[fld] = latent_ids[i] if i < len(latent_ids) else latent_ids[-1]
    wf["30"] = {"class_type": ph, "inputs": ph_in,
                "_meta": {"title": "Phantom 多参考注入"}}

    # 7) 空 latent（T2V/subject 起始潜空间）
    el = info["empty_latent"]
    if el == "EmptyLatentImage":
        el_in = {"width": width, "height": height, "batch_size": 1}
    else:
        el_in = {field_of(s[el], "width"): width,
                 field_of(s[el], "height"): height,
                 field_of(s[el], "num_frames", "frames"): frames}
    wf["31"] = {"class_type": el, "inputs": el_in, "_meta": {"title": "空 latent"}}

    # 8) 采样器
    sm = info["sampler"]
    sms = s[sm]
    sm_in = {field_of(sms, "model"): ["1", 0],
             field_of(sms, "positive"): pos_out,
             field_of(sms, "negative"): neg_out,
             field_of(sms, "latent_image"): ["31", 0],
             field_of(sms, "image_embeds"): ["30", 0],
             field_of(sms, "steps"): steps,
             field_of(sms, "cfg"): cfg,
             field_of(sms, "seed"): seed if seed is not None else int(time.time() * 1000) % (2**32)}
    for f, v in (("sampler_name", "unipc"), ("scheduler", "simple")):
        if f in sms:
            sm_in[f] = v
    if "num_frames" in sms and "num_frames" not in sm_in:
        sm_in["num_frames"] = frames
    wf["32"] = {"class_type": sm, "inputs": sm_in, "_meta": {"title": "Phantom 采样"}}

    # 9) 解码
    de = info["decode"]
    wf["33"] = {"class_type": de,
                "inputs": {field_of(s[de], "samples", "latent"): ["32", 0],
                           field_of(s[de], "vae"): ["2", 0]},
                "_meta": {"title": "VAE 解码"}}

    # 10) 合成视频
    vc = info["video"]
    wf["34"] = {"class_type": vc,
                "inputs": {field_of(s[vc], "images"): ["33", 0],
                           "frame_rate": fps,
                           "filename_prefix": "phantom",
                           "format": "video/h264-mp4",
                           "save_output": True},
                "_meta": {"title": "合成视频"}}
    return wf


# ---------------------------------------------------------------------------
# 提交 / 轮询 / 下载（复用范式）
# ---------------------------------------------------------------------------
def submit_and_wait(host, wf, timeout=1200):
    payload = json.dumps({"prompt": wf, "client_id": "wb_%d" % int(time.time())})
    tmp = "_phantom_payload.tmp"
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
                        print("!!! 执行错误:", json.dumps(m[1], ensure_ascii=False)[:1200])
                        return pid, None
                outs = entry.get("outputs", {})
                for nid, o in outs.items():
                    for v in o.get("videos", []):
                        return pid, (v.get("filename"), v.get("subfolder", ""), v.get("type", "output"))
                    for im in o.get("images", []):
                        if im.get("filename", "").endswith((".mp4", ".webm")):
                            return pid, (im.get("filename"), im.get("subfolder", ""), im.get("type", "output"))
                return pid, None
        time.sleep(5)
    print("!! 超时")
    return pid, None


def download(host, vinfo, dest):
    from urllib.parse import quote
    fn, sub, typ = vinfo
    url = f"{host}/view?filename={quote(fn)}&subfolder={quote(sub)}&type={quote(typ)}"
    code, _ = curl(["-X", "GET", "-o", dest, url], max_time=180)
    if code == "200" and os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    return False


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://43.155.214.240:6889")
    ap.add_argument("--refs", nargs="+", required=True,
                    help="1~4 张参考图（hero + 角度图），全部注入 Phantom")
    ap.add_argument("--prompt", required=True, help="该镜正向提示词（描述动作+场景+角色）")
    ap.add_argument("--neg", default="blurry, low quality, deformed, extra limbs, watermark, text, jpeg artifacts, static")
    ap.add_argument("--out", default="phantom_clip.mp4")
    ap.add_argument("--width", type=int, default=832, help="宽（480p 建议 832，T4 友好）")
    ap.add_argument("--height", type=int, default=480, help="高")
    ap.add_argument("--frames", type=int, default=33, help="帧数（Phantom 默认 81，T4 用 33~49）")
    ap.add_argument("--fps", type=int, default=16)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--cfg", type=float, default=5.0, help="采样 CFG（subject 视频 4~6）")
    ap.add_argument("--phantom-cfg", type=float, default=5.0, help="Phantom 条件 CFG")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="只探测+打印工作流 JSON，不出片不花 GPU")
    a = ap.parse_args()
    host = a.host.rstrip("/")

    if len(a.refs) > 4:
        print("!! Phantom 最多 4 张参考图，已截断前 4 张")
        a.refs = a.refs[:4]

    print("==> 探测 HAI 环境节点 ...")
    info = discover(host)
    missing = [role for role in ("model_loader", "vae_loader", "text_encode",
                                 "image_encode", "phantom", "empty_latent",
                                 "sampler", "decode", "video")
               if not info.get(role)]
    print(f"  节点: " + ", ".join(f"{k}={info.get(k)}" for k in ROLE_CANDIDATES))
    print(f"  模型: model={info.get('files',{}).get('model')} "
          f"vae={info.get('files',{}).get('vae')} "
          f"te={info.get('files',{}).get('text_encoder')}")
    if missing:
        print("❌ 缺必需节点:", missing)
        print("   → 请先在 HAI 跑 hai_phantom_setup.sh 装 ComfyUI-WanVideoWrapper + Phantom 模型，再重启 ComfyUI")
        sys.exit(1)

    uploaded = [upload_image(host, r) for r in a.refs]
    print("参考图已上传:", uploaded)

    wf = build_workflow(uploaded, a.prompt, a.neg, info,
                        width=a.width, height=a.height, frames=a.frames,
                        fps=a.fps, steps=a.steps, cfg=a.cfg,
                        phantom_cfg=a.phantom_cfg, seed=a.seed)

    if a.dry_run:
        print("==> [DRY-RUN] 以下是将提交的工作流 JSON（未出片）：")
        print(json.dumps(wf, ensure_ascii=False, indent=2))
        return

    print(f"提交视频（{a.frames}帧@{a.fps}fps, {a.width}x{a.height}, "
          f"cfg={a.cfg}, phantom_cfg={a.phantom_cfg}）...")
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
