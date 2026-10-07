#!/bin/bash
# ============================================================
#  桃子角色 · MV-Adapter(I2MV)+SDXL 多角度图 续传脚本
#  运行位置：DSW/PAI 实例的终端（/mnt/workspace/ai-comfyui/pai/）
#  用途：① 检查/下载 mv-adapter 单文件  ② 写出图脚本
#        ③ 重启 ComfyUI(6889)  ④ 生成 6 视角图
#  用法：bash resume_mv.sh
# ============================================================
set -e
PAI_DIR=/mnt/workspace/ai-comfyui/pai
MODELS=$PAI_DIR/models
MV_DIR=$MODELS/mv_adapter
MV_FILE=$MV_DIR/mvadapter_i2mv_sdxl.safetensors
OUTDIR=$PAI_DIR/out_mv
COMFY=/root/ComfyUI

echo "=== [1/4] 检查/下载 mv-adapter 单文件 ==="
if [ -f "$MV_FILE" ]; then
  echo "[跳过] 已存在: $MV_FILE ($(du -h "$MV_FILE" | cut -f1))"
else
  mkdir -p "$MV_DIR"
  echo "[下载] huanngzh/mv-adapter::mvadapter_i2mv_sdxl.safetensors (HF 镜像, 禁用 xet)..."
  HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
    huggingface-cli download huanngzh/mv-adapter mvadapter_i2mv_sdxl.safetensors \
    --local-dir "$MV_DIR" --local-dir-use-symlinks False \
    || HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
       python3 -m huggingface_hub.commands.download huanngzh/mv-adapter mvadapter_i2mv_sdxl.safetensors \
       --local-dir "$MV_DIR" --local-dir-use-symlinks False
  echo "[OK] mv-adapter 下载完成"
fi

echo "=== [2/4] 写出图脚本 gen_angles_mv.py ==="
cat > "$PAI_DIR/gen_angles_mv.py" <<'PYEOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV-Adapter (I2MV) + SDXL 从单张参考图生成多视角图，落 out_mv/。"""
import subprocess, json, os, sys, time, uuid
COMFY_IP = os.environ.get("COMFY_HOST", "127.0.0.1")
HOST = f"http://{COMFY_IP}:6889"
CLIENT = uuid.uuid4().hex
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_mv")
os.makedirs(OUTDIR, exist_ok=True)
ANCHOR = os.environ.get("REF_IMG", "peach_role_v6.png")
PROMPT = os.environ.get("MV_PROMPT",
    "a pink peach fruit mascot character, 3d toy figure, soft lighting, clean background")
NEG = "watermark, text, ugly, deformed, blurry, low quality, extra limbs, extra eyes"
NUM_VIEWS = int(os.environ.get("MV_VIEWS", "6"))
SEED = int(os.environ.get("MV_SEED", "12345"))

def api(path, data=None, binary=False, timeout=600):
    cmd = ["curl", "-s", "--noproxy", COMFY_IP, "--max-time", str(timeout), f"{HOST}{path}"]
    if data is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "--data", json.dumps(data)]
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")

def submit(prompt):
    res = json.loads(api("/prompt", {"prompt": prompt, "client_id": CLIENT}))
    if "error" in res:
        raise RuntimeError("提交失败: " + json.dumps(res["error"], ensure_ascii=False))
    return res["prompt_id"]

def wait(prompt_id, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.loads(api(f"/history/{prompt_id}"))
        if prompt_id in h:
            node = h[prompt_id]
            if "status" in node and node["status"].get("status_str") == "error":
                msgs = node["status"].get("messages", [])
                raise RuntimeError("执行出错: " + json.dumps(msgs, ensure_ascii=False))
            return node
        time.sleep(5)
    raise TimeoutError("等待超时 (prompt_id=%s)" % prompt_id)

def download(node):
    files = []
    for nid, o in node.get("outputs", {}).items():
        for img in o.get("images", []):
            url = f"/view?filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img.get('type','')}"
            data = api(url, binary=True, timeout=300)
            path = os.path.join(OUTDIR, img["filename"])
            open(path, "wb").write(data)
            files.append(path)
            print("  已下载:", path, "(%d bytes)" % len(data))
    return files

def build():
    return {
        "1": {"class_type": "DiffusersMVPipelineLoader", "inputs": {
            "ckpt_name": "/mnt/workspace/ai-comfyui/pai/models/sdxl_base",
            "pipeline_name": "MVAdapterI2MVSDXLPipeline"}},
        "3": {"class_type": "DiffusersMVSchedulerLoader", "inputs": {
            "pipeline": ["1", 0], "scheduler_name": "DDPM",
            "shift_snr": True, "shift_mode": "interpolated", "shift_scale": 8}},
        "5": {"class_type": "DiffusersMVVaeLoader", "inputs": {
            "vae_name": "/mnt/workspace/ai-comfyui/pai/models/sdxl_base/vae"}},
        "6": {"class_type": "DiffusersMVModelMakeup", "inputs": {
            "pipeline": ["1", 0], "scheduler": ["3", 0], "autoencoder": ["5", 0],
            "load_mvadapter": True, "adapter_path": "/mnt/workspace/ai-comfyui/pai/models/mv_adapter",
            "adapter_name": "mvadapter_i2mv_sdxl.safetensors", "num_views": NUM_VIEWS}},
        "8": {"class_type": "LoadImage", "inputs": {"image": ANCHOR}},
        "7": {"class_type": "DiffusersMVSampler", "inputs": {
            "pipeline": ["6", 0], "reference_image": ["8", 0],
            "num_views": NUM_VIEWS, "prompt": PROMPT, "negative_prompt": NEG,
            "width": 768, "height": 768, "steps": 50, "cfg": 3, "seed": SEED}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "mv_peach"}},
    }

def main():
    print("[提交] MV-Adapter I2MV (num_views=%d) ..." % NUM_VIEWS)
    pid = submit(build())
    print("  prompt_id=%s" % pid)
    node = wait(pid)
    files = download(node)
    print("\n=== 完成 ===")
    for f in files:
        print(f)

if __name__ == "__main__":
    main()
PYEOF
echo "[OK] gen_angles_mv.py 已就绪"

echo "=== [2.5] 确保参考图在 ComfyUI input 目录 ==="
mkdir -p /root/ComfyUI/input
cp -n "$PAI_DIR/peach_role_v6.png" /root/ComfyUI/input/ 2>/dev/null || true
echo "   参考图: $(ls -la /root/ComfyUI/input/peach_role_v6.png 2>/dev/null | awk '{print $5" bytes"}' || echo '未找到(请先上传 peach_role_v6.png 到 DSW)')"

echo "=== [3/4] 重启 ComfyUI (端口 6889) ==="
pkill -f "main.py" || true
sleep 3
cd "$COMFY" && nohup python3 main.py --port 6889 > /tmp/comfy_run.log 2>&1 &
for i in $(seq 1 40); do
  if curl -s --noproxy 127.0.0.1 http://127.0.0.1:6889/object_info >/dev/null 2>&1; then
    echo "[OK] ComfyUI 已启动"; break
  fi
  sleep 3
done

echo "=== [4/4] 生成 6 视角多角度图 ==="
cd "$PAI_DIR"
python3 gen_angles_mv.py
echo
echo "=== 完成！图片在: $OUTDIR ==="
ls -la "$OUTDIR"
