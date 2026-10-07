#!/usr/bin/env bash
# hai_c1_setup.sh —— 在 HAI 实例内运行（Jupyter 终端 或 SSH）。
# 完成 C1 所需的 "传权重 + clone 插件 + 重启 ComfyUI"。
# 这些动作 ComfyUI 的 HTTP API 做不到，必须 HAI 侧有 shell，所以拆成本脚本。
#
# 用法:
#   1) 复制本脚本到 HAI（cat > hai_c1_setup.sh 粘贴，或 git pull 你的仓库）
#   2) COMFY_ROOT=/path/to/ComfyUI bash hai_c1_setup.sh
#   或默认 /root/ComfyUI
#
# 说明:
#   - 权重改从 hf-mirror 直下（与你在本地下的是同一源），不依赖本机传大文件。
#     若你本机已下好且 HAI 能 SSH，可改成 scp 方式（见文末注释）。
#   - BiRefNet 去背景模型须直连官方 huggingface.co（hf-mirror 未收录）；若 HAI 无外网，改本机 scp 传。
#   - 若 HAI 的 ComfyUI 由平台托管（不是手动 main.py 起的），重启请用平台按钮/命令，
#     删掉本脚本 "3/4 重启" 段即可。

set -e

echo "== 0/4 检测 hf-mirror 连通性（无外网就别烧钱，直接关机）=="
if ! curl -sI --max-time 15 https://hf-mirror.com >/dev/null 2>&1; then
  echo "⚠️ 连不上 hf-mirror —— HAI 实例无外网。"
  echo "   此时权重只能从本机 scp 慢传（11G，且实例在计费），不划算。"
  echo "   👉 请【关机】，告诉我一声，我切到本机 scp 方案再开。"
  exit 1
fi
echo "   连通 OK，继续线上拉取"

COMFY_ROOT="${COMFY_ROOT:-/root/ComfyUI}"
cd "$COMFY_ROOT"
MIRROR="https://hf-mirror.com"
export HF_ENDPOINT="$MIRROR"   # 让 huggingface_hub / git 走镜像

echo "== 1/4 clone ComfyUI-MVAdapter =="
if [ ! -d custom_nodes/ComfyUI-MVAdapter ]; then
  git clone "https://github.com/huanngzh/ComfyUI-MVAdapter" custom_nodes/ComfyUI-MVAdapter || \
  git clone "https://gitee.com/mirrors/ComfyUI-MVAdapter" custom_nodes/ComfyUI-MVAdapter
else
  echo "  已存在, 跳过"
fi

echo "== 2/4 下载权重 (hf-mirror) =="
mkdir -p models/checkpoints models/vae models/mvadapter models/birefnet/ZhengPeng7/BiRefNet
curl -L -C - "$MIRROR/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
     -o models/checkpoints/sd_xl_base_1.0.safetensors
curl -L -C - "$MIRROR/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors" \
     -o models/vae/sdxl_vae.safetensors
curl -L -C - "$MIRROR/huanngzh/mv-adapter/resolve/main/mvadapter_i2mv_sdxl.safetensors" \
     -o models/mvadapter/mvadapter_i2mv_sdxl.safetensors

echo "== 2b BiRefNet 去背景模型 =="
# 注意: hf-mirror 未收录 ZhengPeng7/BiRefNet, 必须直连官方 huggingface.co
HF_ENDPOINT=https://huggingface.co python3 - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("ZhengPeng7/BiRefNet", local_dir="models/birefnet/ZhengPeng7/BiRefNet")
PY

echo "== 3/4 重启 ComfyUI =="
# 若平台托管 ComfyUI，请改用平台重启，注释掉下面三行
pkill -f "main.py --listen" || true
sleep 3
nohup python3 main.py --listen --port=6889 > /tmp/comfy.log 2>&1 &
sleep 8

echo "== 4/4 done =="
curl -s http://127.0.0.1:6889/system_stats | head -c 200
echo
echo "现在把 ComfyUI 地址 (http://<HAI_IP>:6889) 给本机的 hai_c1.py 即可出 9 宫格。"

# ---- 备选: 本机已下好、HAI 可 SSH 时，用 scp 传大文件(不走镜像下载) ----
# 在本机 D:/Aicomfyui 执行:
#   scp models/checkpoints/sd_xl_base_1.0.safetensors root@<HAI_IP>:/root/ComfyUI/models/checkpoints/
#   scp models/vae/sdxl_vae.safetensors                root@<HAI_IP>:/root/ComfyUI/models/vae/
#   scp models/mvadapter/mvadapter_i2mv_sdxl.safetensors root@<HAI_IP>:/root/ComfyUI/models/mvadapter/
#   ssh root@<HAI_IP> "cd /root/ComfyUI && git clone https://github.com/huanngzh/ComfyUI-MVAdapter custom_nodes/ComfyUI-MVAdapter && pkill -f 'main.py --listen'; sleep 3; nohup python3 main.py --listen --port=6889 >/tmp/comfy.log 2>&1 &"
