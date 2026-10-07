#!/usr/bin/env bash
# =============================================================================
# hai_phantom_setup.sh
# 在 HAI（腾讯云 GPU T4，按小时计费）上补齐「Phantom(Wan2.1 1.3B)」视频引擎环境。
#
# 用法（SSH 进 HAI 后执行，或用 HAI Jupyter 的 Terminal 跑）：
#   cd /root/ComfyUI
#   bash /path/to/hai_phantom_setup.sh
#
# 本脚本只做一件事：把本地(你电脑) gen_phantom_clip.py 需要的环境装好。
# 装完请通过 HAI 控制台『重启 ComfyUI』按钮重启，确保加载新插件 WanVideoWrapper。
#
# 模型清单（hf-mirror 国内镜像，比 huggingface.co 稳）：
#   - Phantom-Wan-1.3B            -> models/diffusion_models/Phantom-Wan/   (主模型)
#   - umt5_xxl_fp8_e4m3fn         -> models/text_encoders/                  (文本编码器, ~10GB, 可 CPU offload)
#   - wan_2.1_vae                 -> models/vae/                            (VAE, 仅 250MB)
#   - ComfyUI-WanVideoWrapper     -> custom_nodes/                          (kijai 节点)
#
# T4(15.6G 显存) 可行性：Phantom 1.3B 量化后约 4~6GB，480p 出片约 4~8GB 显存，可吃。
# =============================================================================
set -e

COMFY="${COMFY_ROOT:-/root/ComfyUI}"
CN="$COMFY/custom_nodes"
M="$COMFY/models"
HF="https://hf-mirror.com"

echo "=================================================="
echo " HAI Phantom 环境补齐"
echo " COMFY=$COMFY"
echo "=================================================="

# ---- [0] 磁盘检查：Phantom 全家桶约需 15~20GB ----
echo "==> [0] 磁盘检查"
df -h "$COMFY" | tail -1
AVAIL=$(df -m "$COMFY" | awk 'NR==2 {print $4}')
if [ -n "$AVAIL" ] && [ "$AVAIL" -lt 20000 ]; then
  echo "⚠️  剩余空间 ${AVAIL}MB < 20GB，Phantom 可能装不下！"
  echo "    建议：扩容系统盘，或只下 fp16 主模型 + 跳过可选项。"
  # 不致命退出，继续尝试
fi

# ---- [1] 克隆 / 更新 ComfyUI-WanVideoWrapper (kijai) ----
echo "==> [1] ComfyUI-WanVideoWrapper (kijai dev)"
cd "$CN"
if [ ! -d ComfyUI-WanVideoWrapper ]; then
  git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git
else
  echo "    已存在，git pull 更新"
  (cd ComfyUI-WanVideoWrapper && git pull)
fi
if [ -f ComfyUI-WanVideoWrapper/requirements.txt ]; then
  pip install -r ComfyUI-WanVideoWrapper/requirements.txt || echo "⚠️ requirements 安装失败，手动 pip install 后重试"
fi
cd "$COMFY"

# ---- [2] 建目录 ----
echo "==> [2] 建模型目录"
mkdir -p "$M/diffusion_models/Phantom-Wan" "$M/text_encoders" "$M/vae"

# ---- [3] 下载主模型 Phantom-Wan-1.3B（bytedance 原版 .pth 优先；失败回退 Kijai fp16）----
echo "==> [3] Phantom-Wan-1.3B 主模型"
if [ ! -f "$M/diffusion_models/Phantom-Wan/Phantom-Wan-1.3B.pth" ] && \
   [ ! -f "$M/diffusion_models/Phantom-Wan/Phantom-Wan-1.3B_fp16.safetensors" ]; then
  echo "    尝试 bytedance 原版 .pth ..."
  curl -L -C - -o "$M/diffusion_models/Phantom-Wan/Phantom-Wan-1.3B.pth" \
       "$HF/bytedance-research/Phantom/resolve/main/Phantom-Wan-1.3B.pth" \
    || echo "    .pth 下载失败，回退 Kijai fp16 ..."
  if [ ! -s "$M/diffusion_models/Phantom-Wan/Phantom-Wan-1.3B.pth" ]; then
    rm -f "$M/diffusion_models/Phantom-Wan/Phantom-Wan-1.3B.pth"
    curl -L -C - -o "$M/diffusion_models/Phantom-Wan/Phantom-Wan-1.3B_fp16.safetensors" \
         "$HF/Kijai/WanVideo_comfy/resolve/main/Phantom-Wan-1.3B_fp16.safetensors"
  fi
else
  echo "    已存在，跳过"
fi

# ---- [4] 下载文本编码器 umt5_xxl fp8（~10GB，T4 显存不够可 CPU offload）----
echo "==> [4] umt5_xxl_fp8 文本编码器"
if [ ! -f "$M/text_encoders/umt5_xxl_fp8_e4m3fn.safetensors" ]; then
  curl -L -C - -o "$M/text_encoders/umt5_xxl_fp8_e4m3fn.safetensors" \
       "$HF/Kijai/WanVideo_comfy/resolve/main/umt5_xxl_fp8_e4m3fn.safetensors"
else
  echo "    已存在，跳过"
fi

# ---- [5] 下载 wan_2.1_vae ----
echo "==> [5] wan_2.1_vae"
if [ ! -f "$M/vae/wan_2.1_vae.safetensors" ]; then
  curl -L -C - -o "$M/vae/wan_2.1_vae.safetensors" \
       "$HF/Kijai/WanVideo_comfy/resolve/main/wan_2.1_vae.safetensors"
else
  echo "    已存在，跳过"
fi

# ---- [6] 提醒重启 ----
echo "=================================================="
echo "✅ 下载完成。请执行以下之一重启 ComfyUI 以加载 WanVideoWrapper："
echo "   1) HAI 控制台『重启 ComfyUI』按钮（最稳）"
echo "   2) 或你的启动脚本 / 杀掉 main.py 后用原参数重启"
echo "重启后，在你本地电脑运行："
echo "   python gen_phantom_clip.py --host http://<HAI_IP>:6889 \\"
echo "       --refs hedgehog_hero_cute2.png c1_output/C1_9grid_00001_.png \\"
echo "       --prompt '小刺猬在草地上打滚' --out test.mp4 --dry-run"
echo "（先 --dry-run 看探测到的节点/模型对不对，再去掉 --dry-run 真出片）"
echo "=================================================="
