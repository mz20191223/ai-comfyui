#!/bin/bash
# Tier1 模型全量下载（hf-mirror.com 国内镜像，带断点续传）
# 注意：curl 在 Git Bash 下必须写 Windows 路径 (D:/...) 而非 MSYS 路径 (/d/...)，否则写盘失败
# 用法：在 Git Bash 里  bash download_all_tier1.sh   （后台跑，中断重跑会自动续）
set -u
BASE="D:/Aicomfyui"
MIRROR="https://hf-mirror.com"

mkdir -p "$BASE/models/checkpoints" "$BASE/models/loras" "$BASE/models/vae" "$BASE/models/animatediff"

dl() {
  local out="$1"; local url="$2"
  echo ">>> [$(date +%H:%M:%S)] DOWNLOAD -> $out"
  # -C - 断点续传；--retry 8 次；-m 0 不限时（后台长跑）
  curl -L -C - --retry 8 --retry-delay 10 --retry-all-errors -m 0 \
       -o "$out" "$url" \
       -w "    DONE http=%{http_code} size=%{size_download} time=%{time_total}s\n"
  echo
}

echo "===== 1/4 SDXL 基座 6.5G ====="
dl "$BASE/models/checkpoints/sd_xl_base_1.0.safetensors" \
   "$MIRROR/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"

echo "===== 2/4 皮克斯 LoRA 137M ====="
dl "$BASE/models/loras/Canopus-Pixar-Art.safetensors" \
   "$MIRROR/prithivMLmods/Canopus-Pixar-Art/resolve/main/Canopus-Pixar-Art.safetensors"

echo "===== 3/4 SDXL VAE fp16 fix 335M ====="
dl "$BASE/models/vae/sdxl_vae.safetensors" \
   "$MIRROR/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors"

echo "===== 4/4 AnimateDiff SDXL 动画模块 2.2G ====="
dl "$BASE/models/animatediff/mm_sdxl_v10_beta.ckpt" \
   "$MIRROR/guoyww/AnimateDiff/resolve/main/mm_sdxl_v10_beta.ckpt"

echo "===== 克隆 VideoHelperSuite 视频输出插件 ====="
if [ -d "$BASE/custom_nodes/ComfyUI-VideoHelperSuite/.git" ]; then
  echo "SKIP VHS 已存在"
else
  git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
       "$BASE/custom_nodes/ComfyUI-VideoHelperSuite" 2>&1 | tail -3 || \
  git clone --depth 1 https://ghproxy.com/https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
       "$BASE/custom_nodes/ComfyUI-VideoHelperSuite" 2>&1 | tail -3
fi

echo "===== ALL DONE $(date +%H:%M:%S) ====="
ls -lh "$BASE/models/checkpoints" "$BASE/models/loras" "$BASE/models/vae" "$BASE/models/animatediff"
echo "--- VHS ---"
ls "$BASE/custom_nodes/ComfyUI-VideoHelperSuite" 2>/dev/null | head
