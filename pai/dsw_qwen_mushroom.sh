#!/bin/bash
# DSW 一键：装 Qwen-Image-Edit + 以桃子参考图派生小蘑菇
# 用法：在 DSW 网页终端粘贴本文件内容（含结尾的执行命令）即可，全程自动。
set -u
COMFY=/root/ComfyUI
PAI=/mnt/workspace/ai-comfyui/pai
LOG=/tmp/dsw_qwen_mushroom.log
OUT=$PAI/out_qwen
mkdir -p "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "===== 开始 $(date) ====="

# 0. 检查参考图（用户需先在 DSW 网页把 peach_role_v6.png 上传到 ComfyUI/input）
REF=$COMFY/input/peach_role_v6.png
if [ ! -f "$REF" ]; then
  echo "[错误] 没找到 $REF"
  echo "请先在 DSW 网页终端左侧/文件管理把本地 peach_role_v6.png 上传到 ComfyUI 的 input 目录，再运行本脚本。"
  exit 1
fi
echo "[OK] 参考图: $REF"

# 1. 安装 ComfyUI-GGUF 节点（提供 UnetLoaderGGUF / CLIPLoaderGGUF）
echo "=== [1/6] 安装 ComfyUI-GGUF 节点 ==="
if [ ! -d "$COMFY/custom_nodes/ComfyUI-GGUF" ]; then
  git -C "$COMFY/custom_nodes" clone https://github.com/city96/ComfyUI-GGUF.git
fi
pip install -q -r "$COMFY/custom_nodes/ComfyUI-GGUF/requirements.txt" 2>&1 | tail -3
echo "[OK] ComfyUI-GGUF 就绪"

# 2. 升级 ComfyUI 核心到支持 Qwen-Image 的版本
echo "=== [2/6] 升级 ComfyUI 核心 ==="
cd "$COMFY"
git stash 2>/dev/null || true
git pull 2>&1 | tail -5
pip install -q -r requirements.txt 2>&1 | tail -3
echo "[OK] ComfyUI 已更新: $(git log --oneline -1)"

# 3. 下载三个权重（hf-mirror，禁用 xet；已存在则跳过）
echo "=== [3/6] 下载 Qwen 权重 (hf-mirror) ==="
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
DL() { # $1=repo $2=file $3=localdir
  local f="$3/$2"
  [ -f "$f" ] && { echo "[跳过] 已存在: $f"; return; }
  mkdir -p "$3"
  for try in 1 2 3; do
    echo "[下载#$try] $1/$2 -> $3"
    huggingface-cli download "$1" "$2" --local-dir "$3" --local-dir-use-symlinks False && return
    sleep 2
  done
  echo "[警告] $2 下载失败，稍后可能节点验证不过"
}
DL city96/qwen-image-edit-gguf qwen-image-edit-2511-Q4_K_M.gguf "$COMFY/models/unet"
DL city96/Qwen2.5-VL-7B-Instruct-GGUF Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf "$COMFY/models/text_encoders"
if [ ! -f "$COMFY/models/vae/qwen_image_vae.safetensors" ]; then
  curl -L -C - -o "$COMFY/models/vae/qwen_image_vae.safetensors" \
    https://hf-mirror.com/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors
fi
echo "[OK] 权重清单:"
ls -lh "$COMFY/models/unet/"*.gguf "$COMFY/models/text_encoders/"*.gguf "$COMFY/models/vae/"*.safetensors 2>/dev/null

# 4. 重启 ComfyUI
echo "=== [4/6] 重启 ComfyUI (6889) ==="
pkill -f "main.py" || true
sleep 3
cd "$COMFY" && nohup python3 main.py --port 6889 > /tmp/comfy_run.log 2>&1 &
for i in $(seq 1 60); do
  if curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info >/dev/null 2>&1; then
    echo "[OK] ComfyUI 已启动"; break
  fi
  sleep 3
done

# 5. 验证节点
echo "=== [5/6] 验证 Qwen 节点 ==="
OI=$(curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info)
for n in UnetLoaderGGUF CLIPLoaderGGUF QwenImageSampler QwenImageEmptyLatentImage; do
  if echo "$OI" | grep -q "\"$n\""; then echo "[OK] $n"; else echo "[缺失] $n -> 终止"; exit 1; fi
done

# 6. 派生蘑菇（以桃子为参考，保持风格、换主体）
echo "=== [6/6] 派生蘑菇图 ==="
cat > "$PAI/gen_mushroom.py" <<'PYEOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""以 peach_role_v6 为参考图，Qwen-Image-Edit 派生同风格小蘑菇。"""
import subprocess, json, os, time, uuid
COMFY_IP = "127.0.0.1"
HOST = f"http://{COMFY_IP}:6889"
CLIENT = uuid.uuid4().hex
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_qwen")
os.makedirs(OUTDIR, exist_ok=True)
UNET = "qwen-image-edit-2511-Q4_K_M.gguf"
CLIP = "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
VAE = "qwen_image_vae.safetensors"
ANCHOR = "peach_role_v6.png"
NEG = "low quality, blurry, deformed, extra limbs, bad anatomy, watermark, text, different character, color changed"

POS = ("Keep the EXACT same art style of this reference image (round chibi, Pixar-like 3D render, "
       "soft warm lighting, clean light-gray background). Replace the character with a cute little "
       "MUSHROOM: a red round cap with white polka dots, a round face under the cap brim, big sparkly "
       "eyes, pink blush cheeks, a tiny white chubby body, short stubby legs and round little hands. "
       "Full-body front view, standing, facing the camera, centered composition, consistent style.")

def api(path, data=None, binary=False, timeout=600):
    cmd = ["curl", "-s", "--noproxy", COMFY_IP, "--max-time", str(timeout), f"{HOST}{path}"]
    if data is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "--data", json.dumps(data)]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")

def submit(prompt):
    res = json.loads(api("/prompt", {"prompt": prompt, "client_id": CLIENT}))
    if "error" in res: raise RuntimeError("提交失败: " + json.dumps(res["error"], ensure_ascii=False))
    return res["prompt_id"]

def wait(pid, timeout=1200):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.loads(api(f"/history/{pid}"))
        if pid in h:
            node = h[pid]
            if "status" in node and node["status"].get("status_str") == "error":
                raise RuntimeError("执行出错: " + json.dumps(node["status"].get("messages"), ensure_ascii=False))
            return node
        time.sleep(4)
    raise TimeoutError("等待超时")

def download(node):
    files = []
    for nid, o in node.get("outputs", {}).items():
        for img in o.get("images", []):
            url = f"/view?filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img.get('type','')}"
            data = api(url, binary=True, timeout=300)
            p = os.path.join(OUTDIR, img["filename"]); open(p, "wb").write(data)
            files.append(p); print("  已生成:", p, "(%d bytes)" % len(data))
    return files

def loaders():
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": UNET}},
        "2": {"class_type": "CLIPLoaderGGUF", "inputs": {"clip_name": CLIP, "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "1a": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 1.73}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": POS}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
    }

def build(denoise):
    g = loaders()
    g["6"] = {"class_type": "LoadImage", "inputs": {"image": ANCHOR}}
    g["6b"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["3", 0]}}
    g["7"] = {"class_type": "QwenImageSampler", "inputs": {
        "model": ["1a", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6b", 0],
        "seed": 12345, "steps": 22, "cfg": 6.0, "sampler_name": "euler",
        "scheduler": "normal", "denoise": denoise}}
    g["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}
    g["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "mushroom"}}
    return g

for d in [0.75, 0.85]:
    print(f"[提交] 蘑菇 denoise={d} ...")
    pid = submit(build(d)); print("  prompt_id=", pid)
    files = download(wait(pid))
    for f in files: print("  ->", f)

print("\n=== 蘑菇生成完成 ===")
PYEOF
cd "$PAI" && python3 gen_mushroom.py

# 7. 尝试推 Git 备份（无 credential 则跳过，用户手动发图）
echo "=== [+ ] 尝试 git 备份 ==="
cd "$PAI" && git add out_qwen/ 2>/dev/null && git commit -m "mushroom derived from peach via Qwen on DSW" 2>/dev/null \
  && git push 2>&1 | tail -3 || echo "[跳过] git push 失败(无 credential)，请手动把 out_qwen 下的图发给我"

echo "===== 全部完成 $(date) ====="
echo "蘑菇图目录: $OUT"
ls -lh "$OUT"
echo "日志: $LOG"
